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

## Screenshots
- **Commands**
    - <h4>!id</h4>
    <img src="https://i.imgur.com/iU7VWjg.jpg" width=400>


    - <h4>!link</h4>
    <img src="https://i.imgur.com/Fwchp2T.jpg" width=400>

    - <h4>!linktest</h4>
    <img src="https://i.imgur.com/uKpoPZ1.jpg" width=400>

    - <h4>!nok</h4>
    <img src="https://i.imgur.com/n9ApYPP.jpg" width=400>

    - <h4>!resolution</h4>
    <img src="https://i.imgur.com/7d5Alil.jpg" width=400>
---
- **Events**

    - <h4>Auto Promotion</h4>
    <img src="https://i.imgur.com/VrnDUJr.jpg" width=400>
    <img src="https://i.imgur.com/cFjv52T.jpg" width=400>

    - <h4>VPN Detection</h4>
    <img src="https://i.imgur.com/8VQ2r4U.png" width=400>

    - <h4>Duplicate GUID</h4>
    <img src="https://i.imgur.com/8VQ2r4U.png" width=400>
    
<br><br>
---
<h3>NOTE:</h3>
<b>If your B3 is running on a MySQL server, the required modules should be preinstalled. However in some cases they may not be. If you get any such errors, it may be because of the MySQLdb module. To fix it, in your terminal:</b>

- **For Linux:** `sudo apt-get install python-mysqldb`
- **For Windows:** `pip install mysql-python`