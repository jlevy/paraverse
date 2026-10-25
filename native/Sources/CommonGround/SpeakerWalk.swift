import Foundation
import CoreGraphics

struct SpeakerWalkGraph {
    static let grid: CGFloat = 12
    static let stride = 200
    let points: [CGPoint]
    let neighbors: [[Int]]
    let spawnPoints: [Int]
    let lookup: [Int:Int]

    init() {
        var all = [CGPoint](), ids = [Int:Int]()
        for y in 0...92 { for x in 0...183 {
            let p = CGPoint(x:CGFloat(x)*Self.grid,y:CGFloat(y)*Self.grid)
            if CommonsLayout.walkable(p) { ids[y*Self.stride+x] = all.count; all.append(p) }
        } }
        var edges = Array(repeating:[Int](),count:all.count)
        for (key,index) in ids {
            for offset in [-1,1,-Self.stride,Self.stride] {
                if let next = ids[key+offset], Self.floorSegment(all[index],all[next]) { edges[index].append(next) }
            }
        }
        // Only spawn in the component reachable from the entrance.
        let root = all.indices.min { all[$0].distance(to:CommonsLayout.entrance) < all[$1].distance(to:CommonsLayout.entrance) }!
        var connected:Set<Int> = [root], queue = [root], head = 0
        while head < queue.count {
            let i = queue[head];head += 1
            for next in edges[i] where connected.insert(next).inserted { queue.append(next) }
        }
        let kept = connected.sorted()
        let remap = Dictionary(uniqueKeysWithValues:kept.enumerated().map { ($0.element,$0.offset) })
        points = kept.map { all[$0] }
        neighbors = kept.map { edges[$0].compactMap { remap[$0] } }
        lookup = ids.compactMapValues { remap[$0] }
        let points = self.points
        let spacing: CGFloat = 32
        var slots = [Int]()
        for i in points.indices.sorted(by: { ($0*7919)%points.count < ($1*7919)%points.count }) where CommonsLayout.isActivitySpot(points[i]) {
            if slots.allSatisfy({points[$0].distance(to:points[i]) >= spacing}) { slots.append(i) }
        }
        spawnPoints = slots
    }

    static func floorSegment(_ a:CGPoint,_ b:CGPoint) -> Bool {
        let sampleSpacing:CGFloat = 3
        let count = max(1,Int(ceil(a.distance(to:b)/sampleSpacing)))
        return (0...count).allSatisfy { step in
            let t = CGFloat(step)/CGFloat(count)
            return CommonsLayout.walkable(CGPoint(x:a.x+(b.x-a.x)*t,y:a.y+(b.y-a.y)*t))
        }
    }
    func clearSegment(_ a:CGPoint,_ b:CGPoint) -> Bool { Self.floorSegment(a,b) }
    func nearest(to p:CGPoint, avoiding occupants:[CGPoint] = []) -> Int? {
        let x = Int((p.x/Self.grid).rounded()), y = Int((p.y/Self.grid).rounded())
        return (-2...2).flatMap { dy in (-2...2).compactMap { dx in lookup[(y+dy)*Self.stride+x+dx] } }
            .filter { i in clearSegment(p,points[i]) && occupants.allSatisfy { distanceFromSegment($0,p,points[i]) >= ConferenceCrowd.personalSpace } }
            .min { points[$0].distance(to:p) < points[$1].distance(to:p) }
    }
    func route(from start:Int,to end:Int,avoiding occupants:[CGPoint] = []) -> [Int] {
        let clearance:CGFloat = 23
        var blocked = Set<Int>()
        for p in occupants {
            let x = Int((p.x/Self.grid).rounded()), y = Int((p.y/Self.grid).rounded())
            for dy in -3...3 { for dx in -3...3 {
                if let i = lookup[(y+dy)*Self.stride+x+dx],points[i].distance(to:p)<clearance { blocked.insert(i) }
            } }
        }
        blocked.remove(start)
        guard !blocked.contains(end) else { return [] }
        var parents = Array(repeating:-1,count:points.count), queue = [start],head = 0
        parents[start] = start
        while head<queue.count && parents[end] == -1 {
            let i = queue[head];head += 1
            for next in neighbors[i] where parents[next] == -1 && !blocked.contains(next) {
                parents[next] = i;queue.append(next)
            }
        }
        guard parents[end] != -1 else { return [] }
        var path = [end],node = end
        while node != start {node = parents[node];path.append(node)}
        path.reverse()
        var smooth = [Int](), anchor = 0
        func visible(_ a:CGPoint,_ b:CGPoint)->Bool {
            guard clearSegment(a,b) else {return false}
            return occupants.allSatisfy { distanceFromSegment($0,a,b) >= clearance }
        }
        while anchor<path.count-1 {
            var next = anchor+1
            while next+1<path.count && visible(points[path[anchor]],points[path[next+1]]) {next += 1}
            smooth.append(path[next]);anchor = next
        }
        return smooth
    }
}

extension CGPoint {
    func distance(to other:CGPoint)->CGFloat {hypot(x-other.x,y-other.y)}
}
private func distanceFromSegment(_ p:CGPoint,_ a:CGPoint,_ b:CGPoint)->CGFloat {
    let dx=b.x-a.x,dy=b.y-a.y
    let t=max(0,min(1,((p.x-a.x)*dx+(p.y-a.y)*dy)/max(0.001,dx*dx+dy*dy)))
    return p.distance(to:CGPoint(x:a.x+t*dx,y:a.y+t*dy))
}

struct SpeakerWalker {
    var position:CGPoint
    var direction = 0
    let seed:Int
    var distanceWalked:CGFloat = 0
    var pause:Double
    var speed:CGFloat = 0
    var heading = CGPoint.zero
    var waitingAge:Double = 0
    var route = [Int]()
    var goal:Int?
    var home:Int
    var journey = 0
    var completedTrips = 0
    var blockedTime:Double = 0
    var activity:String
    var destination:String = ""
    var isWalking:Bool { !route.isEmpty }
    init(index:Int,graph:SpeakerWalkGraph) {
        seed=index;home=graph.spawnPoints[index % graph.spawnPoints.count]
        position=graph.points[home]
        pause=Double(index % 17)*0.35
        activity="Looking around"
    }
    mutating func face(_ p:CGPoint) {
        let dx=p.x-position.x,dy=p.y-position.y,bias:CGFloat=1.15
        if abs(dx)>abs(dy)*bias {direction=dx<0 ? 1:2}
        else if abs(dy)>abs(dx)*bias {direction=dy>0 ? 3:0}
    }
}

struct ConferenceCrowd {
    // Limit competing motion while keeping the hall visibly active.
    static let maximumTravelers = 8
    static let personalSpace:CGFloat = 22
    let graph:SpeakerWalkGraph
    var walkers:[SpeakerWalker]
    private var cursor = 0
    private var coffeeLine = [Int]()
    private var coffeeServiceTime:Double = 4
    private let coffeeSlots:[Int]
    init(count:Int) {
        let graph=SpeakerWalkGraph()
        self.graph=graph
        precondition(graph.spawnPoints.count >= count,"The floor needs a distinct clear spot for every attendee")
        coffeeSlots=[CommonsLayout.point(926,126),CommonsLayout.point(941,126),CommonsLayout.point(956,126)].compactMap {graph.nearest(to:$0)}
        walkers=(0..<count).map {SpeakerWalker(index:$0,graph:graph)}
        for i in walkers.indices {settle(i)}
    }
    private mutating func settle(_ i:Int) {
        let p=walkers[i].position
        let space=CommonsLayout.spaces.min {$0.point.distance(to:p)<$1.point.distance(to:p)}!
        switch space.id {
        case "coffee":walkers[i].activity="Taking a coffee break"
        case "stage","judging":walkers[i].activity="Watching a talk"
        case "sponsors":walkers[i].activity="Exploring the booths"
        case "library":walkers[i].activity="Browsing the library"
        case "arcade":walkers[i].activity="Taking an arcade break"
        case "quiet":walkers[i].activity="Taking a quiet break"
        default:walkers[i].activity="Looking around"
        }
        if space.id == "coffee",walkers[i].completedTrips>0,coffeeSlots.contains(walkers[i].home),coffeeLine.count<3 {
            coffeeLine.append(i)
            walkers[i].activity=coffeeLine.first == i ? "Ordering coffee" : "Waiting for coffee"
            walkers[i].face(CommonsLayout.point(850,100))
            return
        }
        if ["commons","discussions","sponsors","mentoring"].contains(space.id),let other=walkers.indices.filter({$0 != i && !walkers[$0].isWalking && walkers[$0].position.distance(to:p)<70})
            .min(by:{walkers[$0].position.distance(to:p)<walkers[$1].position.distance(to:p)}) {
            walkers[i].activity="In conversation"
            walkers[i].face(walkers[other].position)
            walkers[other].face(p)
        } else {walkers[i].face(space.point)}
    }
    private mutating func depart(_ i:Int) -> Bool {
        let nearby=walkers.indices.filter {$0 != i && walkers[$0].position.distance(to:walkers[i].position)<60}.map {walkers[$0].position}
        guard let start=graph.nearest(to:walkers[i].position,avoiding:nearby) else {return false}
        let reserved=Set(walkers.indices.filter {$0 != i}.map {walkers[$0].goal ?? walkers[$0].home})
        let stationary=walkers.indices.filter {$0 != i && !walkers[$0].isWalking}.map {walkers[$0].position}
        walkers[i].journey += 1
        let space=CommonsLayout.spaces[(i+walkers[i].journey)%CommonsLayout.spaces.count]
        let candidates=graph.spawnPoints.filter {
            !reserved.contains($0) && graph.points[$0].distance(to:walkers[i].position)>100 && graph.points[$0].distance(to:walkers[i].position)<650
        }.sorted {
            graph.points[$0].distance(to:space.point) + graph.points[$0].distance(to:walkers[i].position) <
            graph.points[$1].distance(to:space.point) + graph.points[$1].distance(to:walkers[i].position)
        }
        let local=candidates.sorted { graph.points[$0].distance(to:walkers[i].position)<graph.points[$1].distance(to:walkers[i].position) }
        let queueGoals=space.id == "coffee" ? coffeeSlots.filter { !reserved.contains($0) } : []
        for goal in queueGoals+Array(candidates.prefix(10))+Array(local.prefix(10)) {
            let route=graph.route(from:start,to:goal,avoiding:stationary)
            let pathLength=zip([start]+route,route).reduce(CGFloat.zero) { $0+graph.points[$1.0].distance(to:graph.points[$1.1]) }
            if !route.isEmpty && pathLength<800 {
                let destination=CommonsLayout.spaces.min { $0.point.distance(to:graph.points[goal]) < $1.point.distance(to:graph.points[goal]) }!
                walkers[i].waitingAge=0
                walkers[i].route=[start]+route;walkers[i].goal=goal
                walkers[i].destination=destination.title
                walkers[i].activity="Walking to " + destination.title.lowercased()
                walkers[i].blockedTime=0
                return true
            }
        }
        walkers[i].pause=1+Double(i%3)
        return false
    }
    mutating func update(dt:Double,player:CGPoint? = nil) {
        guard dt>0 else {return}
        if let first=coffeeLine.first {
            coffeeServiceTime -= dt
            if coffeeServiceTime<=0 {
                coffeeLine.removeFirst();coffeeServiceTime=4
                walkers[first].activity="Taking a coffee break";walkers[first].pause=2
                if let next=coffeeLine.first {walkers[next].activity="Ordering coffee"}
            }
        }
        var traveling=walkers.filter(\.isWalking).count
        var plans = 0, reroutes = 0
        let departureOrder=walkers.indices.filter { !walkers[$0].isWalking && walkers[$0].pause<=dt }
            .sorted {walkers[$0].waitingAge>walkers[$1].waitingAge}
        let departures=Set(departureOrder.prefix(min(2,max(0,Self.maximumTravelers-traveling))))
        // Rotate priority so the same attendee cannot win every crossing.
        cursor=(cursor+1)%max(1,walkers.count)
        for offset in walkers.indices {
            let i=(offset+cursor)%walkers.count
            if !walkers[i].isWalking {
                if coffeeLine.contains(i) {continue}
                walkers[i].pause=max(0,walkers[i].pause-dt)
                walkers[i].waitingAge += dt
                if departures.contains(i) && traveling<Self.maximumTravelers && plans<2 {
                    plans += 1
                    if depart(i) {traveling += 1}
                }
                continue
            }
            if walkers[i].blockedTime>1.2 && reroutes<2 {
                reroutes += 1
                let occupants=walkers.indices.filter {$0 != i}.map {walkers[$0].position}
                if let start=graph.nearest(to:walkers[i].position,avoiding:occupants),let goal=walkers[i].goal {
                    let detour=graph.route(from:start,to:goal,avoiding:occupants)
                    if !detour.isEmpty {walkers[i].route=[start]+detour;walkers[i].blockedTime=0}
                    else { _ = depart(i) }
                }
            }
            guard let target=walkers[i].route.first else {continue}
            let p=walkers[i].position,q=graph.points[target],distance=p.distance(to:q)
            if distance<0.5 {
                walkers[i].route.removeFirst()
                if walkers[i].route.isEmpty {
                    walkers[i].completedTrips += 1
                    walkers[i].home=walkers[i].goal!;walkers[i].goal=nil
                    walkers[i].pause=3+Double(i%6);walkers[i].speed=0
                    settle(i);traveling -= 1
                }
                continue
            }
            let cruise:CGFloat=34+CGFloat(i%7)*2
            let acceleration:CGFloat=90
            let desired=walkers[i].route.count == 1 ? min(cruise,max(8,sqrt(2*acceleration*distance))) : cruise
            walkers[i].speed=min(desired,walkers[i].speed+acceleration*CGFloat(dt))
            let step=min(distance,walkers[i].speed*CGFloat(dt))
            let desiredHeading=CGPoint(x:(q.x-p.x)/distance,y:(q.y-p.y)/distance)
            let turnBlend:CGFloat=distance<12 ? 1 : min(1,CGFloat(dt)*8)
            if walkers[i].heading == .zero {walkers[i].heading=desiredHeading}
            let hx=walkers[i].heading.x+(desiredHeading.x-walkers[i].heading.x)*turnBlend
            let hy=walkers[i].heading.y+(desiredHeading.y-walkers[i].heading.y)*turnBlend
            let magnitude=max(0.001,hypot(hx,hy)),dx=hx/magnitude,dy=hy/magnitude
            var near=walkers.indices.filter {$0 != i && walkers[$0].position.distance(to:p)<70}.map {walkers[$0].position}
            if let player,player.distance(to:p)<70 {near.append(player)}
            // Prefer forward motion, then a gentle right-hand pass, then the other side.
            let headings:[(CGFloat,CGFloat)]=[(dx,dy),(dx+dy,dy-dx),(dx-dy,dy+dx),(dy,-dx)]
            var accepted:CGPoint?
            for (vx,vy) in headings {
                let length=hypot(vx,vy)
                let next=CGPoint(x:p.x+vx/length*step,y:p.y+vy/length*step)
                if near.allSatisfy({distanceFromSegment($0,p,next)>=Self.personalSpace}) && graph.clearSegment(p,next) {
                    accepted=next;break
                }
            }
            if let next=accepted {
                let moved=p.distance(to:next)
                walkers[i].heading=CGPoint(x:(next.x-p.x)/max(moved,0.001),y:(next.y-p.y)/max(moved,0.001))
                walkers[i].face(next)
                walkers[i].position=next;walkers[i].distanceWalked += moved
                if next.distance(to:q)<distance-0.01 {walkers[i].blockedTime=0}
                else {walkers[i].blockedTime += dt}
            } else {
                walkers[i].speed=max(0,walkers[i].speed-acceleration*CGFloat(dt))
                walkers[i].blockedTime += dt
            }
        }
    }
}
