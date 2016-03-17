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

Then, re-run the reddit installation script:

```bash
cd ~/src/reddit
sudo ./install-reddit.sh
```

Then, copy the upstart scripts:

```bash
sudo cp ~/src/robin/upstart/* /etc/init/
```

Then, enable the consumers:

```bash
cd ~/consumer-counts.d
echo 1 > robin_presence_q
echo 1 > robin_waitinglist_q
sudo initctl emit reddit-start
```

Finally, enable the cron jobs:

```bash
sudo cp ~/src/robin/cron.d/* /etc/cron.d/
```
