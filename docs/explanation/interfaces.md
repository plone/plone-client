---
myst:
  html_meta:
    "description": "When to give an assistant the plone-client MCP server, the command line, or the agent skill, and why the MCP server offers operations instead of one tool per service."
    "property=og:description": "When to give an assistant the plone-client MCP server, the command line, or the agent skill, and why the MCP server offers operations instead of one tool per service."
    "property=og:title": "About the MCP server, the command line, and the skill"
---

(explanation-interfaces)=

# About the MCP server, the command line, and the skill

plone-client gives an assistant three ways into a Plone site: an MCP server, a command line, and an agent skill that teaches the command line.
They share one library, one set of profiles, and the same safety switches, so the choice is about where the assistant runs, not about what it can do.

## Where the assistant runs decides

A coding agent, such as Claude Code, already works in a terminal.
For it, the command line is the natural fit: nothing runs in the background, the exact command is in the transcript for you to repeat, and the same commands serve scripts and CI jobs.
The skill adds what `--help` cannot: the conventions of Plone and Volto, and the habits of a careful editor, such as previewing a change before making it.

A chat assistant, such as Claude Desktop, has no terminal.
The MCP server is how it reaches the site.
It also suits agents that should not run arbitrary commands at all, because the server limits them to the tools it offers.

Nothing stops you from using both.
A coding agent can have the skill for scripting and the server for quick questions about the content.

## Why operations, not one tool per service

`plone.restapi` has more than a hundred services, and plone-client has a method for each.
Turning each method into a tool would hand a model about 125 tools, and models choose worse from long lists.
Most real tasks also take several requests that must happen in a particular order.

Creating a News Item with its images is a good example.
On a Volto site, the News Item has no `image` field: its lead image is an Image stored inside it, which `preview_image_link` points to.
A field the type does not have is silently ignored, so a model that guesses wrong gets an item without an image and no error.
A tool that creates the item, uploads the files, and sets the right field gets it right every time, because the knowledge lives in code rather than in the prompt.

So the server offers seventeen tools: the everyday reads, the operations of {mod}`plone_client.operations`, and one generic tool for any other service.
The operations are ordinary library functions, so scripts and the command line get the same reliability.

## Why every operation reports its requests

An operation that sends ten requests can fail on the seventh.
Rolling back over HTTP is not possible in general, and guessing what was done is worse than knowing.
Every operation therefore returns, or attaches to its error, the list of what it created and every request it sent.
A person can clean up from that list, and a model can decide to resume.

The same list makes a dry run useful: it shows the whole plan, including the items that would be created and the paths they would most likely get.

## One server for several sites

Someone who looks after several sites could register one server per site.
Each server then repeats the same tools under a different name, so the assistant sees the full tool list once per site, and you add a server every time you add a site.

A single server for several sites keeps one set of tools and adds a `site` argument to each, whose values are the profile names.
The assistant learns the sites from `list_sites` and from the server's instructions, which name each site with its description, so a good description is what lets it pick the right site.
Each site keeps its own profile, so a production site can stay read-only while a local site accepts changes, on the same server.

The cost is a new way to go wrong: a tool call with the wrong `site`.
Read-only profiles make that harmless for production, since the server refuses the change before any request is sent.
Where even reads should stay apart, such as sites of different customers, separate servers, or one per group of profiles, keep them apart.

## Learning the blocks of a site

To write a page, an assistant must know which blocks the site has and what data each one takes.
Only the Volto frontend knows that, since add-ons and projects register their own blocks, so Volto 19.6.0 and later have an `@blocks-schema` service that describes them.
On sites with an older Volto, plone-client describes Volto's core blocks from documentation that ships with it, and says so.
An assistant then still writes correct text, image, and teaser blocks, and knows that the site may have more.

## Related

- {ref}`explanation-cli-for-agents` explains what makes the command line safe and efficient for agents.
- {ref}`howto-assistant` connects an assistant through the MCP server.
- {ref}`howto-agents` sets up a coding agent with the command line and the skill.
