"""Minimize the reviewed public attendance announcements for the distributable app."""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

PUBLIC_FIELDS = (
    'id', 'name', 'username', 'profile_url', 'attendance_status', 'attendance_mode',
    'source_url', 'post_date', 'evidence', 'matching_opt_in', 'avatar_asset',
)
REQUIRED_TEXT = PUBLIC_FIELDS[:-2]


def public_attendees(rows):
    if not isinstance(rows, list):
        raise ValueError('Public attendees must be a list')
    result = []
    for row in rows:
        if not isinstance(row, dict) or any(not isinstance(row.get(key), str) or not row[key].strip() for key in REQUIRED_TEXT):
            raise ValueError('Invalid public attendee required field')
        username = row['username']
        if not re.fullmatch(r'[A-Za-z0-9_]{1,15}', username) or row.get('matching_opt_in') is not False:
            raise ValueError('Invalid public attendee identity or opt-in state')
        for key, suffix in (('profile_url', ''), ('source_url', r'/status/\d+')):
            url = urlsplit(row[key])
            if url.scheme != 'https' or url.netloc.lower() not in {'x.com', 'www.x.com', 'twitter.com', 'www.twitter.com'} or url.query or url.fragment or not re.fullmatch('/' + re.escape(username) + suffix + '/?', url.path, re.I):
                raise ValueError('Attendance source must belong to the public profile')
        if row['attendance_mode'] not in {'unspecified', 'in_person'}:
            raise ValueError('Invalid public attendance mode')
        avatar = row.get('avatar_asset')
        if avatar is not None and (not isinstance(avatar, str) or not re.fullmatch(r'attendee-[A-Za-z0-9_-]+', avatar)):
            raise ValueError('Invalid local attendee avatar asset')
        # Whitelist only reviewed UI/attendance fields; no role, synthesis or scraper payload.
        result.append({key: row[key] for key in PUBLIC_FIELDS if key in row})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    rows = public_attendees(json.loads(args.source.read_text()))
    args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
