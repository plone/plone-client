# Changelog

<!--
   You should *NOT* be adding new change log entries to this file.
   You should create a file in the news directory instead.
   For helpful instructions, please see:
   https://github.com/plone/plone.releaser/blob/master/ADD-A-NEWS-ITEM.rst
-->

<!-- towncrier release notes start -->

## 1.0.0a2 (2026-10-28)


### New features:

- Added a `portal_type` argument to the `create_page` MCP tool, so a page can be created as a content type with blocks other than `Document`. @ericof [#12](https://github.com/plone/plone-client/issues/12)
- Added a warning when a profile's credentials are rejected: a profile with a username or token that the site answers as anonymous now makes `plone-client mcp` warn at startup, `site_info` report `credentials_rejected`, and `info` and `profile test` report it with exit code 4, with the command that fixes the secret. @ericof [#13](https://github.com/plone/plone-client/issues/13)
- Added `files` and `lead_image` to `create_page`, in the operation, the MCP tool and the `create-page` command (`--file`, `--lead`, `--no-lead`), so a page can carry uploaded files and a lead image, stored the way the type expects. @ericof [#14](https://github.com/plone/plone-client/issues/14)
- Added MCP tools for services the client already wrapped: `get_workflow` lists the transitions an item can run now, `get_vocabulary` returns the valid values of a choice field, `get_translations`, `link_translation`, and `unlink_translation` manage translations, and `get_working_copy`, `check_out`, `check_in`, and `cancel_working_copy` manage working copies. @ericof [#17](https://github.com/plone/plone-client/issues/17)
- Added the `--tool` option to `plone-client mcp`, which offers only the tools named, so the model reads a shorter list of tools. A tool the server would not offer, such as a misspelled one or a tool that changes a read-only site, stops the command with exit code 3. @ericof [#17](https://github.com/plone/plone-client/issues/17)
- Added MCP tools to edit the blocks of a page without resending all of them: `list_blocks` shows their ids and types, `add_blocks` inserts blocks after a given block or at a position, `update_block` changes one block, `remove_blocks` deletes blocks, and `set_blocks` replaces them while keeping the title and description blocks. They also work on blocks inside grids and other containers. Blocks can now be given as a list, each with an `@type`, to these tools and to `create_content` and `update_content`: ids and the layout are made for you, a string `href` becomes a list of links, and a block without `@type` is refused before anything is sent. The same steps are in the library as `operations.add_blocks`, `update_block`, `remove_blocks`, and `set_blocks`, with the helpers `blocks.normalize`, `tidy`, `locate`, `outline`, and `prepare`. @ericof [#17](https://github.com/plone/plone-client/issues/17)
- Added `plone-client mcp --http`, which serves the MCP server over streamable HTTP for assistants that connect to a URL. Every request needs a bearer token, made with `plone-client mcp-token generate` and kept in the keyring, or given in `PLONE_CLIENT_MCP_TOKEN`. The server listens on `127.0.0.1:8000` unless given `--host` and `--port`, and the sites' own credentials stay in its profiles. @ericof [#18](https://github.com/plone/plone-client/issues/18)
- Added a choice of the block types that Markdown and HTML become, such as code blocks or tables as text: a `blocks` table in a profile sets them for a site, and `--blocks` on `create-page` and `upload-tree`, the `blocks` argument of the MCP tools `create_page` and `upload_tree`, or `blocks_setting` in Python changes them for one call. An unknown block type or option is refused before any request is sent. The `markdown` extra now needs `collective.html2blocks` 1.0.0b1 or later. @ericof [#20](https://github.com/plone/plone-client/issues/20)


### Bug fixes:

- The MCP tools `run_transition`, `move_content`, and `call_service` no longer tell clients that they are idempotent: running them twice does not give the same result, so clients should not retry them on their own. @ericof [#17](https://github.com/plone/plone-client/issues/17)
- MCP tools that work on the same site now run one at a time. Assistants that call several tools at once could mix the requests that two operations reported, or lose a block edit made at the same moment. @ericof 

## 1.0.0a1 (2026-10-27)


### Breaking changes:

- Rewrote the client on `httpx`: one `PloneClient` per site, with the managers as attributes and paths, site URLs, `uid:<UID>` and `resolveuid` links accepted wherever an item is expected. `AsyncPloneClient`, `PloneClientConfig` and the methods for services that `plone.restapi` does not provide were removed, and Python 3.11 is now the minimum. @ericof 


### New features:

- Added `plone_client.operations`, tasks that send several requests in the right order: create an item with files and images inside it and set its lead image, create a page from Markdown or HTML, upload a local folder keeping its structure, and copy or move items with a report. Each operation honors `dry_run` and `read_only`, returns every request it sent, and raises `PloneOperationError` with what was already created when it stops part way. The commands `create-page`, `create-with-files`, and `upload-tree` run them from the command line. @ericof [#9](https://github.com/plone/plone-client/issues/9)
- Added an MCP server, `plone-client mcp`, in the new `mcp` extra: it serves the selected profile over standard input and output, or several sites at once with `--site`, `--group`, or `--all`, offering the everyday reads, the high-level operations, and one tool for any other `plone.restapi` service; changes to read-only profiles are refused. Profiles can now be gathered into named groups in the configuration file, managed with `plone-client profile groups`, `group-set`, and `group-remove`. @ericof [#9](https://github.com/plone/plone-client/issues/9)
- Added `blocks.block`, `blocks.container`, `blocks.grid`, and `blocks.teaser`, to build blocks of any type, including add-on blocks and blocks that hold others, such as a grid of four teasers. `blocks.text` now builds its paragraph with `collective.html2blocks` when the `markdown` extra is installed, and collapses runs of whitespace either way. @ericof [#9](https://github.com/plone/plone-client/issues/9)
- Added `client.block_types` and the `block-types` command, which list the blocks of a Volto site and describe their data from the `@blocks-schema` service of the Volto server, reached through the new `frontend_url` setting. Sites without that service get the documentation of Volto's core blocks instead. The new `markdown` extra converts Markdown and HTML to blocks with `collective.html2blocks`, on Python 3.12 or later. @ericof [#9](https://github.com/plone/plone-client/issues/9)
- Added `plone_client.blocks`, helpers to build Volto blocks and to walk them and their links. @ericof 
- Added `read_only` and `dry_run` modes to `PloneClient`, so a script can refuse or preview every change it would make to a site. @ericof 
- Added an agent skill that teaches coding agents such as Claude Code to work with Plone sites through the command line, installed with `plone-client skill install`. @ericof 
- Added named connection profiles to work with several sites, with passwords kept in the operating system keyring, an environment variable or a command such as a password manager, read-only profiles, a `.plone-client.toml` file that selects the profile of a project, and timeout, retry, and TLS settings per profile or shared by all of them, including a custom CA bundle. @ericof 
- Added the `plone-client` command line, installed with the `cli` extra: read, search, create, change, publish, move, upload and download content, and manage users, groups, the registry and aliases, with JSON output and exit codes meant for scripts and agents. @ericof 
- Grouped the command line help into panels: commands that read, change, or upload content, site administration, advanced requests, and configuration; each command group splits its subcommands into Browse and Write panels. In a terminal the panels are drawn as boxes; when the output goes to a pipe or a file, as for coding agents, the help is plain text with the same groups. @ericof 


### Bug fixes:

- Fixed the requests for copying, moving and ordering content, changing the registry, group membership, undoing transactions and uploading files with TUS, which did not match what `plone.restapi` expects. @ericof 


### Internal:

- Added a `make release` command that releases the package with zest.releaser and publishes it with uv. @ericof 
- Licensed the package under the GPLv2, like Plone. @ericof 
- Moved continuous integration and linting to `uv` and `make` targets, and added the towncrier change log check and Dependabot. @ericof 
- Updated locked dependencies with security fixes: anyio, certifi, idna, Pygments, requests, soupsieve, and urllib3. @ericof 


### Documentation:

- Documented the MCP server, the high-level operations, and the block types: how to connect an assistant, how to create content in one step, how to build any block, a reference of the MCP tools, and an explanation of when to use the MCP server, the command line, or the agent skill. @ericof [#9](https://github.com/plone/plone-client/issues/9)
- Fixed the links to the `plone.restapi` documentation. @ericof 
- Rewrote the documentation following the Plone documentation style and the Diátaxis framework, with the Plone Sphinx theme: tutorials, how-to guides with runnable examples, reference including a compatibility grid with Plone and `plone.restapi` versions and a map to the functions of `@plone/client`, and explanation. @ericof 


### Tests

- Added unit tests that check every request against the `plone.restapi` documentation, and integration tests against Plone 6.0, 6.1, and 6.2 in Docker. @ericof 
- Fixed the agent skill tests on Windows, where paths use backslashes and the home directory comes from `USERPROFILE`. @ericof
