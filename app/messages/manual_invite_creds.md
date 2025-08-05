Hello {{user_data.first_name}},

We are happy to grant you Hack@UCF Private Cloud access!

These credentials can be used to the Hack@UCF Private Cloud. This can be accessed at {{ settings.infra.horizon }} while on the CyberLab WiFi.

```
Username: {{ creds.username or "Not Set" }}
Password: {{ creds.password or ("Please visit https://" + settings.http.domain + "/profile and under Danger Zone, reset your Infra creds.") }}
```

By using the Hack@UCF Infrastructure, you agree to the following Acceptable Use Policy located at https://help.hackucf.org/misc/aup

The password for the `Cyberlab` WiFi is currently `{{ settings.infra.wifi }}`, but this is subject to change (and we'll let you know when that happens).

Happy Hacking,
  - Hack@UCF Bot
