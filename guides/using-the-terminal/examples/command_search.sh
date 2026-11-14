# How a shell finds a command: a builtin first, then each directory of PATH in order.
# The shell does its own search here, on a pretend computer in a temporary folder.

root=$(mktemp -d)
trap 'rm -rf "$root"' EXIT

# A pretend computer: each program, as an empty script in its directory.
for program in /opt/homebrew/bin/python3 /opt/homebrew/bin/uv /usr/local/bin/python3 \
    /usr/bin/python3 /usr/bin/git /usr/bin/ls /bin/cat /bin/ls; do
    mkdir -p "$root$(dirname "$program")"
    printf '#!/bin/sh\n' > "$root$program"
    chmod +x "$root$program"
done

find_command() {
    local name=$1 path=$2 found directory count=0
    if [ "$(type -t "$name")" = builtin ]; then
        echo "  $name: a shell builtin, no search needed"
        return
    fi
    # Ask the shell, in a subshell whose PATH lists the pretend directories.
    found=$(PATH="$root${path//:/:$root}"; command -v "$name")
    IFS=: read -r -a directories <<< "$path"
    for directory in "${directories[@]}"; do
        count=$((count + 1))
        if [ "$found" = "$root$directory/$name" ]; then
            echo "  $name: runs $directory/$name (directory $count of PATH)"
            return
        fi
    done
    echo "  $name: command not found (searched all $count directories)"
}

path=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin
echo "PATH = $path"
for name in python3 git cat cd pyhton3; do
    find_command "$name" "$path"
done

reordered=/usr/bin:/opt/homebrew/bin:/usr/local/bin:/bin
echo "PATH = $reordered"
find_command python3 "$reordered"

short=/usr/bin:/bin
echo "PATH = $short"
find_command uv "$short"
