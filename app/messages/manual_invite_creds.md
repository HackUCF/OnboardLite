Hello {{user_data.first_name}},

We're happy to grant you access to the Hack@UCF Private Cloud! You can reach it at <{{settings.infra.horizon}}> using these credentials:

```yaml
Username: {{creds.get("username") or "Not Set"}}
Password: {{creds.get("password") or "Not Set"}}
```

If no password is listed above, visit <https://{{settings.http.domain}}/profile> and reset your Infra credentials under Danger Zone.

The cloud is only reachable from the CyberLab WiFi or over our VPN. To get connected from anywhere else, follow the setup guide at <https://help.hackucf.org/guides/OpenStack%20Setup%20Guide/>.

The password for the `Cyberlab` WiFi is currently `{{settings.infra.wifi}}`. It does change from time to time, and we'll let you know when it does.

By using the Hack@UCF Infrastructure, you agree to the Acceptable Use Policy at <https://help.hackucf.org/misc/aup>.

Happy Hacking,

Hack@UCF Bot
