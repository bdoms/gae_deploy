Copyright &copy; 2010, [Brendan Doms](http://www.bdoms.com/)  
Licensed under the [MIT license](http://www.opensource.org/licenses/MIT)


GAE Deploy is a project to minify CSS and JavaScript before deploying, as well as handle static file cache-busting in production.

## Deployment

Typical usage to minify CSS and JS files and then run the deployment command looks like this:

```bash
python gae_deploy css_directory js_directory
```

The command line arguments are just a list of directories (relative or absolute) which contain CSS and/or JS files.
For example, you have a single directory with all your static or public assets, called `public`, the command would be:

```bash
python gae_deploy public
```

### Options

#### Relative Paths
The first command line option, `rel`, is to specify a folder or folders that the built URLs should be relative to.
If a single relative folder is supplied then it is used for all directories.
Otherwise a comma separated list must equal the length of the supplied folders so they can be matched up.
For example, if you ran this command:

```bash
python gae_deploy rel=public,static public/css static/js
```
Then the URL for anything in the `css` or `js` directories would not have `public` or `static` in it, respectively. The file `static/js/main.js`
would be referenced as `/js/main.js`.
This effectively strips away unwanted filesystem paths.

#### URL Prefixes

The second command line option, `prefix`, is to specify a prefix or prefixes for the built URLs.
This is very useful for setting up custom URL routing for your assets that does not have to depend on the structure of your files and folders.
This command works the same way as the first, where if a single prefix is supplied then it is used for all directories.
Otherwise a comma separated list must equal the length of the supplied folders so they can be matched up.
For example, if you ran this command:

```bash
python gae_deploy rel=public,static prefix=/cdn1,/cdn2 public/css static/js
```
Then the URL for a file at `public/css/main.css` would be `/cdn1/css/main.css`, and likewise
the URL for a file at `static/js/main.js` would be `/cdn2/js/main.js`.


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
