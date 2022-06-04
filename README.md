# disCOD B3 Plugin

B3 Plugin for [disCOD](https://github.com/Zoro-6191/disCOD)

## **Features**
- Most things configurable
- Players can easily link and unlink anytime they want, however times they want
- Auto promotion to linked people
- **`!reso <player>`** : Find out resolution of a player
- Screenshot sub-plugin (requires ss-upload disCOD plugin, comes presintalled):
    - Announce if a player leaves soon after their ss was taken
    - Get notified when the SS is uploaded on Discord
## Beta Features
- Takes automatic screenshots of non-admins on connecting
- Keeps a check on duplicate GUIDs connecting to the server
- Stores miscellaneous client data (like Steam ID)
- If configured, can block players with VPNs, along with a synced **`!allowvpn`** command to allow specific IDs to use VPN or in case of false positives.
- Discord webhooks for the same

## **How To Install**
- Copy and paste `conf/` and `extplugins/`
- Copy this in `conf/b3.ini` under plugins
    ```
    discod: @conf/plugin_discod.ini
    ```
- Restart B3
---
**NOTE: If your B3 is running on a MySQL server, the required modules should be preinstallled. However in some cases they may not be. If you get any such errors, it may be because of the `MySQLdb` module. To fix it, in your terminal:**
- **For Linux:** `sudo apt-get install python-mysqldb`
- **For Windows:** `pip install mysql-python`