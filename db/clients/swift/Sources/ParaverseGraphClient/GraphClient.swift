import Foundation

/// A JSON value, for result rows whose column types vary by query.
public enum JSONValue: Decodable, Equatable, Sendable {
    case string(String)
    case number(Double)
    case bool(Bool)
    case array([JSONValue])
    case object([String: JSONValue])
    case null

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() { self = .null }
        else if let value = try? container.decode(Bool.self) { self = .bool(value) }
        else if let value = try? container.decode(Double.self) { self = .number(value) }
        else if let value = try? container.decode(String.self) { self = .string(value) }
        else if let value = try? container.decode([JSONValue].self) { self = .array(value) }
        else { self = .object(try container.decode([String: JSONValue].self)) }
    }

    public var string: String? { if case .string(let value) = self { value } else { nil } }
    public var number: Double? { if case .number(let value) = self { value } else { nil } }
    public var array: [JSONValue]? { if case .array(let value) = self { value } else { nil } }
    public var object: [String: JSONValue]? { if case .object(let value) = self { value } else { nil } }
}

/// One entity in a result graph. `id` is the KB's typed ID, such as `person:april-leonard`.
public struct GraphNode: Decodable, Identifiable, Sendable {
    public let id: String
    public let labels: [String]
    public let kind: String?
    public let name: String?
    public let data: [String: JSONValue]
    /// The full softschema payload; present only for the `entity` query.
    public let doc: [String: JSONValue]?
}

public struct GraphLink: Decodable, Sendable {
    public let relationship: String
    public let source: String
    public let target: String
    public let data: [String: JSONValue]
}

public struct ResultGraph: Decodable, Sendable {
    public let nodes: [GraphNode]
    public let links: [GraphLink]
}

/// The response of every named query: a table, plus any nodes and links it returned.
public struct QueryResult: Decodable, Sendable {
    public let query: String
    public let columns: [String]
    public let rows: [[JSONValue]]
    public let graph: ResultGraph

    /// Rows as dictionaries keyed by column name.
    public var records: [[String: JSONValue]] {
        rows.map { Dictionary(uniqueKeysWithValues: zip(columns, $0)) }
    }
}

public struct GraphAPIError: Error, Decodable, Sendable {
    public let error: String
}

/// Runs catalog queries against `paraverse-graph serve` (or the same routes mounted elsewhere).
public struct GraphClient: Sendable {
    public let baseURL: URL

    public init(baseURL: URL = URL(string: "http://127.0.0.1:8766")!) {
        self.baseURL = baseURL
    }

    public func run(_ query: String, _ params: [String: String] = [:]) async throws -> QueryResult {
        var components = URLComponents(
            url: baseURL.appendingPathComponent("api/query/\(query)"), resolvingAgainstBaseURL: false)!
        components.queryItems = params.sorted { $0.key < $1.key }.map { URLQueryItem(name: $0.key, value: $0.value) }
        let (data, response) = try await URLSession.shared.data(from: components.url!)
        if let http = response as? HTTPURLResponse, http.statusCode != 200 {
            throw (try? JSONDecoder().decode(GraphAPIError.self, from: data))
                ?? GraphAPIError(error: "HTTP \(http.statusCode)")
        }
        return try JSONDecoder().decode(QueryResult.self, from: data)
    }
}
