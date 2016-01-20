# robin

April Fools 2016

## Installation

Install the plugin itself.

```bash
cd ~/src/robin
python setup.py build
sudo python setup.py develop
```

Then add the plugin to your ini file:

```diff
############################################ PLUGINS
# which plugins are enabled (they must be installed via setup.py first)
-plugins = about, liveupdate
+plugins = about, liveupdate, robin
```
