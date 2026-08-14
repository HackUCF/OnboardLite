Hello {{user_data.first_name}}, and welcome to Hack@UCF!

This message confirms that your membership has processed successfully. You can view and edit your membership ID at <https://{{settings.http.domain}}/profile>.

One of the perks of paying dues is access to the Hack@UCF Private Cloud at <{{settings.infra.horizon}}>, using these credentials:

```yaml
Username: {{creds.get("username") or "Not Set"}}
Password: {{creds.get("password") or "Not Set"}}
```

The cloud is only reachable from the CyberLab WiFi or over our VPN. To get connected from anywhere else, follow the setup guide at <https://help.hackucf.org/guides/OpenStack%20Setup%20Guide/>.

The password for the `Cyberlab` WiFi is currently `{{settings.infra.wifi}}`. It does change from time to time, and we'll let you know when it does.

New to all this? The rest of our guides live at <https://help.hackucf.org>.

By using the Hack@UCF Infrastructure, you agree to the Acceptable Use Policy at <https://help.hackucf.org/misc/aup>.

Happy Hacking,

Hack@UCF Bot
