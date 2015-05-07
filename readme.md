Copyright &copy; 2010-2015, [Brendan Doms](http://www.bdoms.com/)  
Licensed under the [MIT license](http://www.opensource.org/licenses/MIT)


GAE Deploy is a project to minify CSS and JavaScript before deploying, as well as handle static file cache-busting in production.

It can also write out simple template files and optionally deploy a specific git branch or multiple branches at once.

## Deployment

Typical usage to minify CSS and JS files and to deploy the current branch looks like this:

```bash
python gae_deploy deploy.yaml --gae /path/to/gae
```

### Command Line Arguments

#### YAML Configuration File

The first argument is a path to a YAML file that contains configuration information about the assets you want gae_deploy to minimize and keep track of. It is required.

#### GAE Path

The `--gae` option (shortcut `-g`) is a path to where the Google App Engine SDK is on your system.
It is required if yaml is not installed, so that gae_deploy can use the yaml library included with GAE.
However if yaml is installed on your system and accessible to Python, then this argument can safely be ommitted.

#### Git Branch

The `--branch` option (shortcut `-b`) specifies a git branch to deploy.
If this option is not included then by default the current branch will be used.
If git is not installed on the system or the current directory is not a repository then the app is simply deployed as is.

#### List of Git Branches

The `--list` option (shortcut `-l`) specifies a named list of git branches to deploy.
Lists are defined in the configuration file. Each list is simply a list of branch names.
Branches will be deployed in the order they are listed.

#### Write Out Templates

The `--templates` option (shortcut `-t`) writes out the template files for the current branch specified in the configuration file.
It is useful for testing and verifying template file output as it does not deploy anything.

### Configuration

The configuration file contains information about how the deploy should be performed both for static files and optionally for git branches.

There is an example provided, `deploy.yaml`, which you can use to get started by copying and pasting into your application directory and then modifying to suit your needs.

#### Git Branches

The `branches` directive describes how git branches should be deployed.

##### Default Branch

The `default` option specifies a branch to use as a fallback in case parameters are not defined for another branch.
If a default is available it will always be used if a branch's own options can't be found.
If a default is not defined then if a branch has no definitions it will not be deployable.

A default is useful for feature branches, where you might want to quickly put up a new branch without worrying about its configuration.

##### Template Files List

The `files` option is a list of templates to use for swapping out variables and writing new files per branch.
Each entry has an `input`, which is a path to the template file and an `output`, which is where the final version should be written.

Output files are overwritten without warning.

##### Branch-Specific Variables

The `variables` option contains a list of branches, each with a list of its own variables to swap out in the template files.
Variables take the form of `${variable_name}` in a template file.

There are two special cases for variables. The first is if a variable is named `_version` then its value will be the app version when that branch is deployed. This overwrites any version specified in the app.yaml file.

The second special case is if a variable's value is `_branch` then the branch name will be used.
This can be used in combination with the `_version` option on a `default` branch to make it so that a branch without a specific version (or one configured) will use its name as its version.

#### Static Directories

A list of `static_dirs` is used to look for static assets (CSS and JS files) to minify.
Each entry contains a required `path` attribute that specifies where to find the directory.

##### Relative Paths

The `rel` attribute is an optional attribute to specify for a folder what the built URLs should be relative to.
For example, if you included this:

```yaml
- path: public/css
  rel: public
```
Then the URL for any assets in the `css` directory would not have `public` in it. The file `public/css/main.css`
would be referenced as `/css/main.css`.
This effectively strips away unwanted filesystem paths.

##### URL Prefixes

The `prefix` attribute is an optional attribute to specify a path to prefix the built URLs with.
This is very useful for setting up custom URL routing for your assets that does not have to depend on the structure of your files and folders.
For example, if you included this:

```yaml
- path: public/css
  rel: public
  prefix: cdn
```
Then the URL for a file at `public/css/main.css` would be `/cdn/css/main.css`.

#### Symbolic Paths

The `symbolic_paths` option is a way of routing one generated URL onto another.
This allows for having multiple different references to the same file. For example, with this configuration:

```yaml
symbolic_paths:
- path: local/css/development.css
  link: cdn/css/production.css
```

The file `development.css` could still be referenced in templates like `${static('local/css/development.css')}`
but the final output would be `cdn/css/production.css`.

#### Trello Integration

If you include the Trello subsection then cards from a "Done" list will automatically be moved to a new release list.
You can see how to get the required values in the readme of [the Trello submodule](https://github.com/bdoms/trello).

Also note that the values are run through an `eval` statement, which allows you to store them elsewhere.
This means you don't have to commit the `api_key` or `oauth_token` to code,
or that you can have different ones on different machines. For example:

```yaml
trello:
  api_key: os.environ['TRELLO_API_KEY']
  oauth_token: os.environ['TRELLO_OAUTH_TOKEN']
  board_id: 'normal_string'
```

The extra, optional parameters are:

 * `release_name` - the name of the new card. Gets sent through `strftime` with the current local date and time
so that they can be included in the name if desired.
 * `branches` - a list of branches to act on when pushed. All other branches will be ignored.
For example, this lets you move cards when master is pushed but not feature branches.

## Cache-Busting

To get at the ability to cache-buste, first make sure that your `app.yaml` file contains a very long expiration, such as:

```yaml
default_expiration: "1000d"
```

Then, in your templates or wherever you reference a static asset do this:

```python
from gae_deploy import static
<script type="text/javascript" src="${static('/path/to/asset.js')}"></script>
```

The static method will properly serve minified versions in production, non-minified versions in development, and can
even handle assets it's not aware of, like images.
