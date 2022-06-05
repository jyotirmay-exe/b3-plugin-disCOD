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
    ![!id](https://cdn.discordapp.com/attachments/773013374647926784/982674948021682247/Screenshot_86.png)

    - <h4>!link</h4>
    ![!link](https://cdn.discordapp.com/attachments/773013374647926784/982674946989887568/Screenshot_84.png) <br>
    ![!link](https://cdn.discordapp.com/attachments/773013374647926784/982933371527245865/Screenshot_85.png)

    - <h4>!linktest</h4>
    ![!linktest](https://cdn.discordapp.com/attachments/773013374647926784/982674945937137684/Screenshot_81.png)

    - <h4>!nok</h4>
    ![!nok](https://cdn.discordapp.com/attachments/773013374647926784/982674946176221234/Screenshot_82.png)

    - <h4>!resolution</h4>
    ![!reso](https://cdn.discordapp.com/attachments/773013374647926784/982676824096133160/Screenshot_83.png)
---
- **Events**

    - <h4>Auto Demotion</h4>
    ![](https://cdn.discordapp.com/attachments/773013374647926784/982674948285939782/Screenshot_87.png)

    - <h4>Auto Promotion</h4>
    ![](https://cdn.discordapp.com/attachments/773013374647926784/982674945517699082/Screenshot_88.png)

    - <h4>VPN Detection</h4>
    ![](https://cdn.discordapp.com/attachments/773013374647926784/982678233097048195/Screenshot_89_copy.png)
    <br>
    <img src="https://cdn.discordapp.com/attachments/773013374647926784/982923326827675668/IMG_20220605_135606.png" width=582>
<br><br>
---
<h3>NOTE:</h3>
<b>If your B3 is running on a MySQL server, the required modules should be preinstalled. However in some cases they may not be. If you get any such errors, it may be because of the MySQLdb module. To fix it, in your terminal:</b>

- **For Linux:** `sudo apt-get install python-mysqldb`
- **For Windows:** `pip install mysql-python`