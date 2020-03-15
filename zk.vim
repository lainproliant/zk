" VIM Plugin for Lain's Zettelkasten.
" Last Change: 03/14/20 12:24
" Maintainer: Lain Musgrove (lainproliant)
" License: MIT

"if exists("g:loaded_zk") || &cp
"  finish
"endif

" -------------------------------------------------------------------
let g:loaded_zk = 1
let s:save_cpo = &cpo
set cpo&vim

" -------------------------------------------------------------------
if !hasmapto('<Plug>ZKOpenUnderCursor')
  map <unique> <Leader>g <Plug>ZKOpenUnderCursor
endif
noremap <unique> <script> <Plug>ZKOpenUnderCursor <SID>OpenUnderCursor
noremap <SID>OpenUnderCursor :call <SID>OpenRef(expand("<cWORD>"))<CR>

" -------------------------------------------------------------------
if !exists(":ZKOpen")
  command -nargs=1 ZKOpen :call s:Open(<q-args>)
endif

" -------------------------------------------------------------------
function s:OpenRef(zettel_ref)
  " Verify that the zettel_ref is actually a reference,
  " then extract the zettel_id from the ref.
  if matchstr(a:zettel_ref, "zk@\\([[:alnum:]_-]\\)\\+") != ""
    call s:Open(split(a:zettel_ref, "@")[1])
  else
    echom "Not a zettel ref: \"" . a:zettel_ref . "\""
  endif

endfunction

" -------------------------------------------------------------------
function s:Open(zettel_id)
  let zettel_file = trim(system("zk prepare " . a:zettel_id))
  if v:shell_error != 0
    echom "ZK: Failed to prepare zettel."
    return
  endif

  let current_win = winnr()
  let max_win = winnr("$")

  if max_win == 1
    vsplit
  else
    wincmd p
  endif

  exe "e " . zettel_file
endfunction

" -------------------------------------------------------------------
let &cpo = s:save_cpo
unlet s:save_cpo
