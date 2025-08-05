Hello {{user_data.first_name}}, and welcome to Hack@UCF!

This message is to confirm that your membership has processed successfully. You can access and edit your membership ID at https://{{settings.http.domain}}/profile.

These credentials can be used to the Hack@UCF Private Cloud, one of our many benefits of paying dues. This can be accessed at {{settings.infra.horizon}} while on the CyberLab WiFi.

```yaml
Username: {{creds.get("username", "Not Set")}}
Password: {{creds.get("password", f"Not Set")}}
```

The password for the `Cyberlab` WiFi is currently `{{settings.infra.wifi}}`, but this is subject to change (and we'll let you know when that happens).

If you need any help getting started there are instructions here https://help.hackucf.org.

By using the Hack@UCF Infrastructure, you agree to the Acceptable Use Policy located at https://help.hackucf.org/misc/aup

Happy Hacking,
  - Hack@UCF Bot
