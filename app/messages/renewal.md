Hello {{user_data.first_name}}, and welcome back to Hack@UCF!

This message confirms that your membership renewal has processed successfully. You can view and edit your membership ID at <https://{{settings.http.domain}}/profile>.

Your Hack@UCF Private Cloud account is active again, and your credentials have not changed. The same username and password you had before will still work at <{{settings.infra.horizon}}>. If you've forgotten your password, reset it at <{{settings.keycloak.url}}/realms/{{settings.keycloak.realm}}/login-actions/reset-credentials>.

The cloud is only reachable from the CyberLab WiFi or over our VPN. To get connected from anywhere else, follow the setup guide at <https://help.hackucf.org/guides/OpenStack%20Setup%20Guide/>.

The password for the `Cyberlab` WiFi is currently `{{settings.infra.wifi}}`. It does change from time to time, and we'll let you know when it does.

If you need a refresher, the rest of our guides live at <https://help.hackucf.org>.

By using the Hack@UCF Infrastructure, you agree to the Acceptable Use Policy at <https://help.hackucf.org/misc/aup>.

Happy Hacking,

Hack@UCF Bot
