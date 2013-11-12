Copyright &copy; 2010, [Brendan Doms](http://www.bdoms.com/)  
Licensed under the [MIT license](http://www.opensource.org/licenses/MIT)


GAE Deploy is a project to minify CSS and JavaScript before deploying, as well as handle static file cache-busting in production.

## Deployment

Typical usage to minify CSS and JS files and then run the deployment command looks like this:

```bash
python gae_deploy css_directory js_directory
```

The command line arguments are just a list of directories (relative or absolute) which contain CSS and/or JS files.
If you have a single directory with all your static or public assets, this becomes even simpler:

```bash
python gae_deploy public
```

There is a single command line option, `rel`, which is to specify a folder or folders that the built URLs should be relative to.
If a single relative folder is supplied then it is used for all directories.
Otherwise a comma separated list must match the length of the supplied folders so they can be matched up.
For example, if you ran this command:

```bash
python gae_deploy rel=public,static public/css static/js
```

Then the URL for anything in the `css` or `js` directories would not have `public` or `static` in it, respectively. The file `static/js/main.js`
would be referenced as `/js/main.js`.

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

