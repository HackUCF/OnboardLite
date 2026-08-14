Hello {{user_data.first_name or "there"}},

You're almost a Hack@UCF member! Not everything is checked off yet:

- Provided your name: {{'✅' if user_data.first_name else '❌'}}
- Signed the ethics form: {{'✅' if user_data.ethics_form.signtime != 0 else '❌'}}
- Paid $10 dues: {{'✅' if user_data.did_pay_dues else '❌'}}

Once everything above has a checkmark, head to <https://{{settings.http.domain}}/profile> to re-run this check and finish up.

If you think you've already done all of it, reach out to an Exec on the Hack@UCF Discord and we'll sort it out.

We hope to see you soon,

Hack@UCF Bot
