Copyright &copy; 2010, [Brendan Doms](http://www.bdoms.com/)  
Licensed under the [MIT license](http://www.opensource.org/licenses/MIT)


GAE Deploy is a project to minify CSS and JavaScript before deploying, as well as handle static file cache-busting in production.

## Deployment

Typical usage to minify CSS and JS files and then run the deployment command looks like this:

```bash
python gae_deploy gae=/path/to/gae config=gae_deploy.yaml
```

### Command Line Arguments

#### GAE Path

The `gae` command line argument is a path to where the Google App Engine SDK is on your system.
It is required if yaml is not installed, so that gae_deploy can use the yaml library included with GAE.
However if yaml is installed on your system and accessible to Python, then this argument can safely be ommitted.

#### YAML Configuration File

The `config` argument is a path to a yaml file that contains configuration imformation about the assets you want gae_deploy to minimize and keep track of. It is required.

### Configuration

The main part of the configuration file is a list of `static_dirs`, each containing a required `path` attribute that specifies where to find the directory.

There is an example provided, `gae_deploy.yaml`, which you can use to get started by copying and pasting into your application directory and then modifying to suit your needs.

#### Relative Paths

The `rel` attribute is an optional attribute to specify for a folder what the built URLs should be relative to.
For example, if you included this:

```yaml
- path: public/css
  rel: public
```
Then the URL for any assets in the `css` directory would not have `public` in it. The file `public/css/main.css`
would be referenced as `/css/main.css`.
This effectively strips away unwanted filesystem paths.

#### URL Prefixes

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
