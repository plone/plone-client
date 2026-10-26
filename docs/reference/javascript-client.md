---
myst:
  html_meta:
    "description": "How the methods of plone-client map to the functions of @plone/client, the JavaScript client for plone.restapi."
    "property=og:description": "How the methods of plone-client map to the functions of @plone/client, the JavaScript client for plone.restapi."
    "property=og:title": "Map to @plone/client"
    "keywords": "Plone, plone.restapi, @plone/client, JavaScript, TypeScript, Python"
---

(reference-plone-client-map)=

# Map to `@plone/client`

[`@plone/client`](https://www.npmjs.com/package/@plone/client) is the JavaScript and TypeScript client for `plone.restapi`, used by Volto and Seven.
This page maps its functions, as of version 2.0.0-alpha.8, to the methods of plone-client, so you can move between the two.

## Conventions

| | `@plone/client` | plone-client |
|---|---|---|
| Create a client | `PloneClient.initialize({ apiPath, token })` | `PloneClient(url, username=…, password=…)` |
| Log in | `login({ data: { login, password } })`, then pass the token | `auth_method="jwt"`, or a `token` |
| Call style | A flat method on the client: `cli.getContent(…)` | A method on a manager: `client.content.get(…)` |
| Names | A verb and a noun: `getX`, `createX`, `updateX`, `deleteX` | The noun is the manager, the verb is the method: `x.get`, `x.create`, `x.update`, `x.delete` |
| Lists | `getXs` or `getAllX` | `x.list` |
| Arguments | One object: `{ path, data }` | The item first, then keyword arguments: `(ref, …)` |
| Item | `path` | `ref`: a path, a URL, `uid:<UID>`, or a `resolveuid` link |
| Result | A promise of `{ status, data }` | The decoded JSON, directly |
| Errors | A rejected promise with `{ status, data: { type, message } }` | An exception per status, with `status_code`, `error_type`, and `message` |
| Execution | Asynchronous | Synchronous |

The rule of thumb: `cli.getComments({ path })` in JavaScript is `client.comments.list(path)` in Python, and `cli.createComment({ path, data })` is `client.comments.create(path, …)`.

## Content

| Service | `@plone/client` | plone-client |
|---|---|---|
| `GET` item | `getContent({ path, expand, fullObjects, version })` | {meth}`content.get(ref, expand=…, fullobjects=…, version=…) <plone_client.managers.content.ContentManager.get>` |
| `POST` item | `createContent({ path, data })` | {meth}`content.create(parent, portal_type, data) <plone_client.managers.content.ContentManager.create>` |
| `PATCH` item | `updateContent({ path, data })` | {meth}`content.update(ref, data) <plone_client.managers.content.ContentManager.update>` |
| `DELETE` item | `deleteContent({ path })` | {meth}`content.delete(ref) <plone_client.managers.content.ContentManager.delete>` |
| `@copy` | `copyContent({ path, data })` | {meth}`content.copy(source, target) <plone_client.managers.content.ContentManager.copy>` |
| `@move` | `moveContent({ path, data })` | {meth}`content.move(source, target) <plone_client.managers.content.ContentManager.move>` |
| `PATCH` `ordering` | `updateContent({ path, data: { ordering } })` | {meth}`content.order(folder, obj_id, delta) <plone_client.managers.content.ContentManager.order>` |
| `@linkintegrity` | `getLinkintegrity({ uids })` | {meth}`content.link_integrity(uids) <plone_client.managers.content.ContentManager.link_integrity>` |
| `GET @lock` | `getLock({ path })` | {meth}`content.lock_info(ref) <plone_client.managers.content.ContentManager.lock_info>` |
| `POST @lock` | `createLock({ path, data })` | {meth}`content.lock(ref) <plone_client.managers.content.ContentManager.lock>` |
| `PATCH @lock` | `updateLock({ path, locktoken })` | {meth}`content.refresh_lock(ref) <plone_client.managers.content.ContentManager.refresh_lock>` |
| `DELETE @lock` | `deleteLock({ path, data })` | {meth}`content.unlock(ref) <plone_client.managers.content.ContentManager.unlock>` |

## Search

| Service | `@plone/client` | plone-client |
|---|---|---|
| `@search` | `search({ query })` | {meth}`search.search(path, …) <plone_client.managers.search.SearchManager.search>`, {meth}`search.iter <plone_client.managers.search.SearchManager.iter>` for every page |
| `@querystring` | `getQuerystring()` | {meth}`querystring.config() <plone_client.managers.search.QuerystringManager.config>` |
| `@querystring-search` | `querystringSearch({ query })` | {meth}`querystring.search(query) <plone_client.managers.search.QuerystringManager.search>` |

## Workflow, history, and working copies

| Service | `@plone/client` | plone-client |
|---|---|---|
| `GET @workflow` | `getWorkflow({ path })` | {meth}`workflow.get(ref) <plone_client.managers.workflow.WorkflowManager.get>` |
| `POST @workflow/<transition>` | `createWorkflow({ path, transition, data })` | {meth}`workflow.transition(ref, transition) <plone_client.managers.workflow.WorkflowManager.transition>` |
| `GET @history` | `getHistory({ path })` | {meth}`history.list(ref) <plone_client.managers.workflow.HistoryManager.list>` |
| `GET @history/<version>` | `getHistoryVersion({ path, version })` | {meth}`history.get(ref, version) <plone_client.managers.workflow.HistoryManager.get>` |
| `PATCH @history` | `revertHistory({ path, data })` | {meth}`history.revert(ref, version) <plone_client.managers.workflow.HistoryManager.revert>` |
| `GET @workingcopy` | `getWorkingcopy({ path })` | {meth}`working_copy.get(ref) <plone_client.managers.workflow.WorkingCopyManager.get>` |
| `POST @workingcopy` | `createWorkingcopy({ path })` | {meth}`working_copy.create(ref) <plone_client.managers.workflow.WorkingCopyManager.create>` |
| `PATCH @workingcopy` | `checkInWorkingcopy({ path })` | {meth}`working_copy.check_in(ref) <plone_client.managers.workflow.WorkingCopyManager.check_in>` |
| `DELETE @workingcopy` | `deleteWorkingcopy({ path })` | {meth}`working_copy.delete(ref) <plone_client.managers.workflow.WorkingCopyManager.delete>` |

## Navigation

| Service | `@plone/client` | plone-client |
|---|---|---|
| `@navigation` | `getNavigation({ path, depth })` | {meth}`navigation.navigation(ref, depth=…) <plone_client.managers.navigation.NavigationManager.navigation>` |
| `@breadcrumbs` | `getBreadcrumbs({ path })` | {meth}`navigation.breadcrumbs(ref) <plone_client.managers.navigation.NavigationManager.breadcrumbs>` |
| `@contextnavigation` | `getContextNavigation({ path })` | {meth}`navigation.contextnavigation(ref) <plone_client.managers.navigation.NavigationManager.contextnavigation>` |
| `@navroot` | `getNavroot({ path, language })` | {meth}`navigation.navroot(ref) <plone_client.managers.navigation.NavigationManager.navroot>` |
| `@actions` | `getActions({ path })` | {meth}`navigation.actions(ref) <plone_client.managers.navigation.NavigationManager.actions>` |

## Comments, translations, aliases, and relations

| Service | `@plone/client` | plone-client |
|---|---|---|
| `GET @comments` | `getComments({ path })` | {meth}`comments.list(ref) <plone_client.managers.discussion.CommentsManager.list>` |
| `POST @comments` | `createComment({ path, in_reply_to, data })` | {meth}`comments.create(ref, text, reply_to=…) <plone_client.managers.discussion.CommentsManager.create>` |
| `PATCH @comments/<id>` | `updateComment({ path, comment_id, data })` | {meth}`comments.update(ref, comment_id, text) <plone_client.managers.discussion.CommentsManager.update>` |
| `DELETE @comments/<id>` | `deleteComment({ path, comment_id })` | {meth}`comments.delete(ref, comment_id) <plone_client.managers.discussion.CommentsManager.delete>` |
| `GET @translations` | `getTranslation({ path })` | {meth}`translations.get(ref) <plone_client.managers.discussion.TranslationsManager.get>` |
| `POST @translations` | `linkTranslation({ path, data })` | {meth}`translations.link(ref, translation) <plone_client.managers.discussion.TranslationsManager.link>` |
| `DELETE @translations` | `unlinkTranslation({ path, data })` | {meth}`translations.unlink(ref, language) <plone_client.managers.discussion.TranslationsManager.unlink>` |
| `GET @aliases` on the root | `getAllAliases()` | {meth}`aliases.list() <plone_client.managers.discussion.AliasesManager.list>` |
| `GET @aliases` on an item | `getAliases({ path })` | {meth}`aliases.list(ref) <plone_client.managers.discussion.AliasesManager.list>` |
| `POST @aliases` on an item | `createAlias({ path, data })` | {meth}`aliases.create(ref, aliases) <plone_client.managers.discussion.AliasesManager.create>` |
| `POST @aliases` on the root | `createAliases({ data })` | {meth}`aliases.create_redirects(redirects) <plone_client.managers.discussion.AliasesManager.create_redirects>` |
| `DELETE @aliases` | `deleteAliases({ path, data })` | {meth}`aliases.delete(ref, aliases) <plone_client.managers.discussion.AliasesManager.delete>` |
| `GET @relations` | `getAllRelations()`, `getRelations({ source, relation, onlyBroken })` | {meth}`relations.list(…) <plone_client.managers.discussion.RelationsManager.list>` |
| `POST @relations` | `createRelations({ data })` | {meth}`relations.create(relations) <plone_client.managers.discussion.RelationsManager.create>` |
| `DELETE @relations` | `deleteRelations({ data })` | {meth}`relations.delete(…) <plone_client.managers.discussion.RelationsManager.delete>` |
| `POST @relations/rebuild` | `fixRelations({ data })` | {meth}`relations.rebuild(flush=…) <plone_client.managers.discussion.RelationsManager.rebuild>` |

## Users, groups, and sharing

| Service | `@plone/client` | plone-client |
|---|---|---|
| `GET @users` | `getUsers({ query, groupsFilter, search, limit })` | {meth}`users.list(…) <plone_client.managers.users.UsersManager.list>` |
| `GET @users/<id>` | `getUser({ id })` | {meth}`users.get(user_id) <plone_client.managers.users.UsersManager.get>` |
| `POST @users` | `createUser({ data })` | {meth}`users.create(username, data) <plone_client.managers.users.UsersManager.create>` |
| `PATCH @users/<id>` | `updateUser({ id, data })` | {meth}`users.update(user_id, data) <plone_client.managers.users.UsersManager.update>` |
| `DELETE @users/<id>` | `deleteUser({ id })` | {meth}`users.delete(user_id) <plone_client.managers.users.UsersManager.delete>` |
| `POST @users/<id>/reset-password`, to email a link | `resetPassword({ id })` | {meth}`users.reset_password(user_id) <plone_client.managers.users.UsersManager.reset_password>` |
| `POST @users/<id>/reset-password`, with the old password | `updatePassword({ id, data })` | {meth}`users.update_password(user_id, new_password, old_password=…) <plone_client.managers.users.UsersManager.update_password>` |
| `POST @users/<id>/reset-password`, with a reset token | `resetPasswordWithToken({ id, data })` | {meth}`users.update_password <plone_client.managers.users.UsersManager.update_password>` does not take a token yet |
| `@userschema` | `getUserschema()` | {meth}`users.schema() <plone_client.managers.users.UsersManager.schema>` |
| `GET @groups` | `getGroups()` | {meth}`groups.list() <plone_client.managers.users.GroupsManager.list>` |
| `GET @groups/<id>` | `getGroup({ id })` | {meth}`groups.get(group_id) <plone_client.managers.users.GroupsManager.get>` |
| `POST @groups` | `createGroup({ data })` | {meth}`groups.create(groupname, data) <plone_client.managers.users.GroupsManager.create>` |
| `PATCH @groups/<id>` | `updateGroup({ id, data })` | {meth}`groups.update(group_id, data) <plone_client.managers.users.GroupsManager.update>`; {meth}`groups.add_members <plone_client.managers.users.GroupsManager.add_members>` and {meth}`groups.remove_members <plone_client.managers.users.GroupsManager.remove_members>` for membership |
| `DELETE @groups/<id>` | `deleteGroup({ id })` | {meth}`groups.delete(group_id) <plone_client.managers.users.GroupsManager.delete>` |
| `GET @sharing` | `getSharing({ path, search })` | {meth}`sharing.get(ref, search=…) <plone_client.managers.users.SharingManager.get>` |
| `POST @sharing` | `updateSharing({ path, data })` | {meth}`sharing.update(ref, entries) <plone_client.managers.users.SharingManager.update>` |
| `@principals` | `getPrincipals({ search })` | {meth}`sharing.principals(search) <plone_client.managers.users.SharingManager.principals>` |
| `@roles` | `getRoles()` | {meth}`sharing.roles() <plone_client.managers.users.SharingManager.roles>` |

## Types and vocabularies

| Service | `@plone/client` | plone-client |
|---|---|---|
| `GET @types` | `getTypes()` | {meth}`types.list() <plone_client.managers.types.TypesManager.list>` |
| `GET @types/<type>` | `getType({ type })` | {meth}`types.get(portal_type) <plone_client.managers.types.TypesManager.get>` |
| `GET @types/<type>/<field>` | `getTypeField({ contentFieldPath })` | {meth}`types.get_field(portal_type, name) <plone_client.managers.types.TypesManager.get_field>` |
| `POST @types/<type>` | `createTypeField({ contentPath, data })` | {meth}`types.create_field(portal_type, data) <plone_client.managers.types.TypesManager.create_field>` |
| `PATCH @types/<type>` | `updateTypeField({ contentPath, data })` | {meth}`types.update(portal_type, data, name=…) <plone_client.managers.types.TypesManager.update>` |
| `GET @vocabularies` | `getVocabularies()` | {meth}`vocabularies.list() <plone_client.managers.types.VocabulariesManager.list>` |
| `GET @vocabularies/<name>` | `getVocabulary({ path, title, token, tokens, b_size })` | {meth}`vocabularies.get(name, …) <plone_client.managers.types.VocabulariesManager.get>`, {meth}`vocabularies.iter <plone_client.managers.types.VocabulariesManager.iter>` for every page |
| `@sources/<field>` | `getSource({ path, field })` | {meth}`vocabularies.source(ref, field) <plone_client.managers.types.VocabulariesManager.source>` |
| `@querysources/<field>` | `getQuerysources({ path, field, query })` | {meth}`vocabularies.querysource(ref, field, query) <plone_client.managers.types.VocabulariesManager.querysource>` |

## Site administration

| Service | `@plone/client` | plone-client |
|---|---|---|
| `GET @registry` | `getRegistry()` | {meth}`registry.list() <plone_client.managers.site.RegistryManager.list>` |
| `GET @registry/<name>` | `getRegistryRecord({ name })` | {meth}`registry.get(key) <plone_client.managers.site.RegistryManager.get>` |
| `PATCH @registry` | `updateRegistry({ data })` | {meth}`registry.update(values) <plone_client.managers.site.RegistryManager.update>` |
| `GET @controlpanels` | `getControlpanels()` | {meth}`controlpanels.list() <plone_client.managers.site.ControlpanelsManager.list>` |
| `GET @controlpanels/<id>` | `getControlpanel({ id })` | {meth}`controlpanels.get(panel) <plone_client.managers.site.ControlpanelsManager.get>` |
| `POST @controlpanels/<id>` | `createControlpanel({ path, data })` | {meth}`controlpanels.create(panel, data) <plone_client.managers.site.ControlpanelsManager.create>` |
| `PATCH @controlpanels/<id>` | `updateControlpanel({ path, data })` | {meth}`controlpanels.update(panel, data) <plone_client.managers.site.ControlpanelsManager.update>` |
| `DELETE @controlpanels/<id>` | `deleteControlpanel({ path, data })` | {meth}`controlpanels.delete(panel, item) <plone_client.managers.site.ControlpanelsManager.delete>` |
| `GET @addons` | `getAddons()` | {meth}`addons.list() <plone_client.managers.site.AddonsManager.list>` |
| `GET @addons/<id>` | `getAddon({ id })` | {meth}`addons.get(addon) <plone_client.managers.site.AddonsManager.get>` |
| `POST @addons/<id>/install` | `installAddon({ id })` | {meth}`addons.install(addon) <plone_client.managers.site.AddonsManager.install>` |
| `POST @addons/<id>/uninstall` | `uninstallAddon({ id })` | {meth}`addons.uninstall(addon) <plone_client.managers.site.AddonsManager.uninstall>` |
| `POST @addons/<id>/upgrade` | `upgradeAddon({ id })` | {meth}`addons.upgrade(addon) <plone_client.managers.site.AddonsManager.upgrade>` |
| `POST @addons/<id>/<profile>` | `installAddonProfile({ id, profile })` | {meth}`addons.install_profile(addon, profile) <plone_client.managers.site.AddonsManager.install_profile>` |
| `GET @content-rules` | `getRules()` | {meth}`content_rules.get(ref) <plone_client.managers.site.ContentRulesManager.get>` |
| `POST @content-rules/<id>` | `createRule({ ruleId })` | {meth}`content_rules.assign(ref, rule_id) <plone_client.managers.site.ContentRulesManager.assign>` |
| `PATCH @content-rules` | `updateRules({ data })` | {meth}`content_rules.enable <plone_client.managers.site.ContentRulesManager.enable>`, {meth}`disable <plone_client.managers.site.ContentRulesManager.disable>`, {meth}`apply_to_subfolders <plone_client.managers.site.ContentRulesManager.apply_to_subfolders>`, {meth}`move <plone_client.managers.site.ContentRulesManager.move>` |
| `DELETE @content-rules` | `deleteRules({ data })` | {meth}`content_rules.unassign(ref, rule_ids) <plone_client.managers.site.ContentRulesManager.unassign>` |
| `@site` | `getSite()` | {meth}`system.site() <plone_client.managers.site.SystemManager.site>` |
| `@system` | `getSystem()` | {meth}`system.system() <plone_client.managers.site.SystemManager.system>` |
| `@database` | `getDatabase()` | {meth}`system.database() <plone_client.managers.site.SystemManager.database>` |
| `GET @transactions` | `getTransactions()` | {meth}`system.transactions() <plone_client.managers.site.SystemManager.transactions>` |
| `PATCH @transactions` | `revertTransactions({ data })` | {meth}`system.revert_transactions(transaction_ids) <plone_client.managers.site.SystemManager.revert_transactions>` |
| `GET @upgrade` | `getUpgrade()` | {meth}`system.upgrade_info() <plone_client.managers.site.SystemManager.upgrade_info>` |
| `POST @upgrade` | `runUpgrade({ data })` | {meth}`system.upgrade(dry_run=…) <plone_client.managers.site.SystemManager.upgrade>` |
| `@email-send` | `emailSend({ data })` | {meth}`system.email_send(…) <plone_client.managers.site.SystemManager.email_send>` |
| `@email-notification` | `emailNotification({ user, data })` | {meth}`system.email_notification(…) <plone_client.managers.site.SystemManager.email_notification>` |
| `POST @login` | `login({ data })` | `PloneClient(…, auth_method="jwt")` logs in by itself |

## Only in plone-client

| plone-client | Does |
|---|---|
| {meth}`content.children <plone_client.managers.content.ContentManager.children>`, {meth}`exists <plone_client.managers.content.ContentManager.exists>`, {meth}`find_by_uid <plone_client.managers.content.ContentManager.find_by_uid>`, {meth}`resolve <plone_client.managers.content.ContentManager.resolve>`, {meth}`sort <plone_client.managers.content.ContentManager.sort>` | Conveniences built on `@search` and `PATCH`. |
| {meth}`search.count <plone_client.managers.search.SearchManager.count>` | The number of results of a search. |
| {class}`files <plone_client.managers.files.FilesManager>` | Uploads, `@tus-upload`, `@tus-replace`, downloads, and image scales. |
| {meth}`navigation.inherit <plone_client.managers.navigation.NavigationManager.inherit>` | `@inherit`. |
| {meth}`translations.locate <plone_client.managers.discussion.TranslationsManager.locate>` | `@translation-locator`. |
| {meth}`relations.stats <plone_client.managers.discussion.RelationsManager.stats>` | `GET @relations` without a filter, as counts. |
| {meth}`types.addable <plone_client.managers.types.TypesManager.addable>`, {meth}`replace <plone_client.managers.types.TypesManager.replace>`, {meth}`delete_field <plone_client.managers.types.TypesManager.delete_field>` | Addable types, and `PUT` and `DELETE` on `@types`. |
| {meth}`users.portrait <plone_client.managers.users.UsersManager.portrait>` | `@portrait`. |
| {meth}`system.login_providers <plone_client.managers.site.SystemManager.login_providers>` | `GET @login`. |

## Only in `@plone/client`

| `@plone/client` | Does |
|---|---|
| `resetPasswordWithToken({ id, data })` | Sets a new password with the token from a reset email. |
| `PloneClient.extend({ … })` | Adds methods for add-on services to the client class. |

## Related

- {ref}`reference-managers` lists every manager of plone-client.
- {ref}`howto-call-other-services` calls services neither client covers.
