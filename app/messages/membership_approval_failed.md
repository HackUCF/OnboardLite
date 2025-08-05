Hello {{user_data.first_name}},

We wanted to let you know that you **did not** complete all of the steps for being able to become an Hack@UCF member.

- Provided a name: {{'✅' if user_data.first_name else '❌'}}
- Signed Ethics Form: {{'✅' if user_data.ethics_form.signtime != 0 else '❌'}}
- Paid $10 dues: ✅

Please complete all of these to become a full member. Once you do, visit https://{{settings.http.domain}}/profile to re-run this check.

If you think you have completed all of these, please reach out to an Exec on the Hack@UCF Discord.

We hope to see you soon,
  - Hack@UCF Bot
