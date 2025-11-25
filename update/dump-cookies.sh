#!/usr/bin/env bash

OUTPUT="$HOME/repo/random-2hu-stuff/update/cookies.txt"

{
	echo '# Netscape HTTP Cookie File' # needed by yt-dlp

	# There is no attempt to url encode $1, but SQLite already handles
	# characters like spaces, so only ? % and # should cause issues.
	sqlite3 -separator '	' "file:${1:-$HOME/.local/share/qutebrowser}/webengine/Cookies?nolock=1" "
SELECT
    host_key,
    IIF(host_key LIKE '.%', 'TRUE', 'FALSE'),
    path,
    IIF(is_secure, 'TRUE', 'FALSE'),
    IIF(expires_utc == 0, 0, expires_utc / 1000000 - 11644473600),
    name,
    value
FROM cookies;"
} >"$OUTPUT"

# expires_utc is converted from the Windows NT Time Format to a UNIX timestamp
