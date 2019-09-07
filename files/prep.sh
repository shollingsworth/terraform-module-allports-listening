#!/usr/bin/env bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

chown -Rv root:root /tmp/files
# sync files into root (same pathing)
# https://unix.stackexchange.com/a/83595
# This caused A LOT of pain, when I tried using rsync, beware
cd /tmp/files
find . -type f | cpio --verbose -pdm  /

cat <<'EOF' > /etc/vimrc
filetype on
syntax enable
filetype plugin on
set nocompatible
set autoread
set autoindent
set expandtab
set modeline
set shiftwidth=4
set softtabstop=4
set tabstop=4
filetype plugin indent on
EOF

# export /usr/local/bin/ which is where we put a lot of our scripts
cat <<'EOF' > /etc/profile.d/sh.local
export PATH="$PATH:/usr/local/bin:/usr/local/sbin"
EOF


# Makde some helper scripts
cat <<'EOF' > /usr/local/bin/tailmem
#!/usr/bin/env bash
while true; do free -m| grep '^Mem'; sleep .1; done
EOF

cat <<'EOF' > /usr/local/bin/tail_recent
#!/usr/bin/env bash
tail -F \$(find /var/log -type f -mmin -10)
EOF

chmod -v +x /usr/local/bin/*
chmod -v +x /usr/local/sbin/*
