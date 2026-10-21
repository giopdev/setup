#
# ~/.bashrc
#

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

alias ls='eza --color=auto'
alias ll='eza --icons --long --header --color=auto'
alias la='eza --icons --long -d --header .*'
alias lsa='eza --icons --long --header -a --color=auto'
alias lr='eza --icons --recurse --long --header --color=auto'

alias catl='bat | less -R'

# Other stuff
alias ..='cd ..'
alias df='df -h'
alias cp='cp -i'
alias mv='mv -i'
alias rm='rm -i'
# Change vim -> nvim
alias vim='nvim'
# Git stuff
alias gs='git status'
# output the last clipboard image to a file
alias pasteimage='wl-paste --type image/png >'


alias grep='grep --color=auto'

alias gs='git status'

alias ..='cd ..'

eval "$(starship init bash)"

if [[ -r "${XDG_CONFIG_HOME:-$HOME/.config}/bash/fzf.sh" ]]; then
    source "${XDG_CONFIG_HOME:-$HOME/.config}/bash/fzf.sh"
fi

export EDITOR="/bin/nvim"

function md() {
  if [[ -z "$1" || ! -f "$1" ]]; then
    echo "Usage: md <markdown-file>" >&2
    return 1
  fi

  local name out pandoc_config
  pandoc_config="${XDG_CONFIG_HOME:-$HOME/.config}/pandoc"
  name=$(basename "$1")
  out=$(mktemp --suffix=.html "${TMPDIR:-/tmp}/${name%.*}-XXX") || return

  pandoc "$1" -o "$out" \
    --standalone \
    --embed-resources \
    --css="$pandoc_config/md-preview.css" \
    --include-after-body="$pandoc_config/mermaid.html" \
    --syntax-highlighting=pygments \
    --math-method=mathjax || return

  setsid --fork xdg-open "$out" </dev/null >/dev/null 2>&1
}


# # BASH syntax
# function md() {
#   local name=$(basename "$1")
#   pandoc "$1" > "/tmp/$name.html"
#   xdg-open "/tmp/$name.html"
# }

# Open the remote repository page (GitHub/GitLab/etc.) in the default browser
gopen() {
  local url
  url=$(git config --get remote.origin.url 2>/dev/null) || {
    echo "gopen: not a git repository (or no 'origin' remote)" >&2
    return 1
  }

# Convert SSH URLs (git@host:user/repo.git) to HTTPS
  if [[ "$url" =~ ^git@([^:]+):(.+)$ ]]; then
    host="${BASH_REMATCH[1]}"
    path="${BASH_REMATCH[2]}"
    path="${path%.git}"
    url="https://$host/$path"
  elif [[ "$url" =~ ^ssh://([^@]+@)?([^/:]+)(:[0-9]+)?[/:](.+)$ ]]; then
    host="${BASH_REMATCH[2]}"
    path="${BASH_REMATCH[4]}"
    path="${path%.git}"
    url="https://$host/$path"
  else
    url="${url%.git}"
    if [[ "$url" == git://* ]]; then
      url="https://${url#git://}"
    fi
  fi

  echo "Opening: $url"
  # Detach the opener from this shell and its terminal.
  setsid --fork xdg-open "$url" </dev/null >/dev/null 2>&1
}
