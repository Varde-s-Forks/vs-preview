With VIM
--------

``vs-preview`` is intended to work with an IDE that can use an integrated terminal.
One IDE that can do that is Vim.

Requirements
^^^^^^^^^^^^

The following programs must be installed before you begin:

* `Vim <https://www.vim.org/download.php>`_

Configuring Vim
^^^^^^^^^^^^^^^

1. Associate ``.vpy`` files with Vim
    1. Right-click a ``.vpy`` file and press ``Open with > Choose another app``
    2. Check "Always use this app to open .vpy files"
    3. Scroll down and click "More apps", then "Look for another app on this PC"
    4. Browse to your Vim install location and press "Open"

.. note::

   To get correct syntax highlighting, add `au BufReadPost,BufNewFile *.vpy setlocal syntax=python` to your `_vimrc`.

Running your script
^^^^^^^^^^^^^^^^^^^

.. note::

    The easiest way to run your .vpy file in Vim is by adding `:map r :w<enter>:!vspreview "%:p"<enter>` to your `_vimrc` and pressing `r` in Vim.

1. Open your ``_vimrc``
2. Add ``:map r :w<enter>:!vspreview "%:p"<enter>`` to your ``_vimrc`` file

You can now open the VapourSynth script you want to run in Vim
and run ``vs-preview`` by pressing ``r``.

If everything works properly,
it should open up a terminal at the bottom of the screen
and start printing something like this:

.. code-block:: powershell

    2021-03-19 03:43:03.324: INFO: QSS file successfuly loaded.
    2021-03-19 03:43:03.328: INFO: Found application patches to be applied.
    2021-03-19 03:43:04.207: INFO: No storage found. Using defaults.

If there's an error with your script,
it will print it in the terminal.
If your script is fine,
it will open ``vs-preview`` with the current script.


.. note::

    In the simple configuration above, vs-preview will not run asynchronously, meaning that vim/neovim will be frozen until vs-preview is quit. In Vim 8 (or later) and Neovim, it's possible to start vs-preview asynchronously by having the following lines in your ``_vimrc`` file.

.. code-block:: vimscript
    :linenos:

    nnoremap r :w<enter>:call AsynchronousVsPreview(expand("%:p"))<enter>

    function! AsynchronousVsPreview(file_path)
        let l:vsPreview_cmd = 'vspreview '.a:file_path 
        if exists('g:job_vs')
            if has('nvim')
                call jobstop(g:job_vs)
            else
                call job_stop(g:job_vs)
            endif
            unlet g:job_vs
            echom 'Stopping vs-preview...'
        else
            if has('nvim')
                let g:job_vs = jobstart(l:vsPreview_cmd, {})
            else
                let g:job_vs = job_start(l:vsPreview_cmd, {})
            endif
            echom 'Starting vs-preview asynchronously...'
        endif
    endfunction
