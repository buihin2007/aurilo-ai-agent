# Aurilo Closing Variance Agent — Setup Guide
---

## 1. Prerequisites

- **Python 3.11+**, on PATH
- **Node.js 18+ (LTS)** — to run n8n

## 2. Unzip to the exact path

**Extract so the project folder sits at exactly `C:\aurilo-ai-agent`** — that is,
`C:\aurilo-ai-agent\scripts\`, `C:\aurilo-ai-agent\data\`, and so on.

Right-click the zip → **Properties** → tick **Unblock** if present →
**Extract All…** → set the destination to `C:\`.

Verify this file exists afterwards:

```
C:\aurilo-ai-agent\scripts\ingest_ITDS.py
```

Should not end up with `C:\aurilo-ai-agent\aurilo-ai-agent\`
## 3. Python environment

```
cd C:\aurilo-ai-agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

The workflows call `.venv\Scripts\python.exe` explicitly, so the virtual
environment must be named `.venv` and live inside the project folder.

## 4. Install n8n and set three environment variables

```
npm install -g n8n
```

**Windows (PowerShell):**

```
setx NODES_EXCLUDE "[]"
setx N8N_RESTRICT_FILE_ACCESS_TO "C:\aurilo-ai-agent"
setx GENERIC_TIMEZONE "Europe/Helsinki"
```

Close and reopen the terminal afterwards — `setx` writes to the registry
and does not affect an already-open window.

What each does, and what breaks without it:

- **`NODES_EXCLUDE`** — n8n disables the Execute Command and file
  read/write nodes by default. Without this, no Python step can run.
- **`N8N_RESTRICT_FILE_ACCESS_TO`** — the folders n8n's file nodes may
  touch. Leaving it unset does **not** mean "unrestricted": it falls back
  to `~/.n8n-files` only, and every read from `output\` fails with
  *"Access to the file is not allowed"*.
- **`GENERIC_TIMEZONE`** — the timezone the Schedule Triggers run in.
  Without it n8n uses its own default and "09:00 on the 5th" fires at the
  wrong local hour.

Then start n8n:

```
n8n start
```

Once it has started, press **`o`** in that terminal to open n8n in your
browser, or go to `http://localhost:5678` yourself. Leave the terminal
window open — closing it stops n8n. Section 10 makes it start
automatically instead.

**On first launch n8n asks you to create an owner account** (email +
password). This is local to this installation — not a Microsoft account,
and not connected to us. Store the credentials where your team can find
them: there is no password reset, and losing them means losing access to
the workflows and their run history.

## 5. Import the workflows to n8n

In n8n: **Workflows → Import from File**, once per file in `workflows\`:

- `ITDS Monthly Pipeline.json`
- `Scanning for replies & Send commentary pipeline.json`
- `Error Handler.json`

**Press Ctrl+S after each import** — an imported workflow is not saved
automatically, and navigating away loses it.

**Then connect the Error Handler.** Importing it does nothing on its own.
For *each* of the two other workflows: open it → **Settings** tab → **Error
Workflow** → select `Error Handler`. Without this, any failure is left unnoticed.


## 6. Setting up credentials in n8n

Click any node showing a credential warning (e.g. "Post Questions in
Teams") → Credential dropdown → **+ Create new credential**.

These are the values of the App Registration created for this pilot.
Both Microsoft credentials use the same three.

### Microsoft Teams OAuth2 API

| Field | Value |
|---|---|
| OAuth Redirect URL | `http://localhost:5678/rest/oauth2-credential/callback` |
| Authorization URL | `https://login.microsoftonline.com/779fd0ca-9067-49da-8991-9cde176b7f1d/oauth2/v2.0/authorize` |
| Access Token URL | `https://login.microsoftonline.com/779fd0ca-9067-49da-8991-9cde176b7f1d/oauth2/v2.0/token` |
| Client ID | 332179a3-cff0-42d6-ac1b-7b2f50f48c23 |
| Authentication | choose `Client Secret` |
| Client Secret | JHd8Q~Ds.foPcJQGwzoAxXxAWTMkrkMeQ3oZZb-l |
| Allowed HTTP Requests Domains | choose `All` |
| Microsoft Graph API Base URL | choose `Global (https://graph.microsoft.com)` |
| Custom Scopes | **on** |
| Scope | `openid offline_access ChannelMessage.Send ChannelMessage.Read.All` |

Then click **Connect** — the button sits just above the OAuth Redirect
URL field — and sign in as **agent-pilot@aurilo.fi**. Whichever account
you sign in with is the one the agent posts as.

### Microsoft SharePoint OAuth2 API

| Field | Value |
|---|---|
| OAuth Redirect URL | `http://localhost:5678/rest/oauth2-credential/callback` |
| Authorization URL | `https://login.microsoftonline.com/779fd0ca-9067-49da-8991-9cde176b7f1d/oauth2/v2.0/authorize` |
| Access Token URL | `https://login.microsoftonline.com/779fd0ca-9067-49da-8991-9cde176b7f1d/oauth2/v2.0/token` |
| Client ID | 332179a3-cff0-42d6-ac1b-7b2f50f48c23 |
| Authentication | choose `Client Secret` |
| Client Secret | JHd8Q~Ds.foPcJQGwzoAxXxAWTMkrkMeQ3oZZb-l |
| Allowed HTTP Requests Domains | choose `All` |
| Custom Scopes | **on** |
| Enabled Scopes | `openid offline_access https://graph.microsoft.com/Sites.ReadWrite.All` |
| Subdomain | `turuntietokeskus` |

Then click **Connect** — the button sits just above the OAuth Redirect
URL field — and sign in as **agent-pilot@aurilo.fi**. Whichever account
you sign in with is the one the agent posts as.


### Redirect URI

Both credentials use
`http://localhost:5678/rest/oauth2-credential/callback`, which is already
registered on the App Registration. n8n uses port 5678 unless `N8N_PORT`
is set; the credential dialog shows the exact OAuth Redirect URL it will
use. If it differs from the one above, add that URL to the App
Registration too, or Connect fails with `AADSTS500113`.

### SMTP

Used in two places: the **Send Draft Commentary** node in *Scanning for
replies & Send commentary pipeline*, and the **Send Email** node in
*Error Handler*. One credential covers both — create it once, then select
it on the second node from the Credential dropdown.

Mail is sent from the same service account used everywhere else:

| Field | Value |
|---|---|
| User | `agent-pilot@aurilo.fi` |
| Password | -&UG8Mb2gNl*rzM88ZVh=b |
| Host | `smtp.office365.com` |
| Port | `587` |
| SSL/TLS | **off** |
| Client Host Name | leave empty |

**Change the port from the default.** n8n pre-fills `465` with SSL/TLS
on; Exchange Online does not accept implicit TLS on 465. Use port `587`
with SSL/TLS switched off — n8n then negotiates STARTTLS, which is what
Microsoft expects.

**SMTP AUTH has to be enabled on the `agent-pilot@aurilo.fi` mailbox.**
Microsoft disables it by default. If Connect fails with an
authentication error, that is almost always the cause — your Exchange
admin can enable it per mailbox.

Set the recipient on each node: in *Error Handler*, whoever should hear
about failed runs; in *Send Draft Commentary*, the named Finance
reviewer.


## 7. Add the P&L owners to the Teams channel

The agent asks each question by naming the person responsible for that
part of the P&L, and waits for them to reply in the thread. They have to
be able to see the channel for that to work.

The owner of the *Aurilo Finance Agent* team should add these four to the
team, so they have access to `ClosingVariance QA`:

| Owner | P&L area |
|---|---|
| Erkki Kondelin | Total Revenue |
| Kaisu Kaarnajoki | Cost of Goods Sold |
| Ville Tiainen | Non-Operating Income, Depreciations and Amortizations |
| Ari Jaatinen | Personnel Expenses, Operative Expenses, and anything unmapped |

`data\itds\owner_mapping.json` is what decides this. It is plain JSON
keyed by P&L area — edit it directly if responsibilities change, no code
change required.

## 8. Run the test

The sample ITDS export is already in `data\itds\`, so there is nothing to
prepare. Run it in this order:

**1. Execute *ITDS Monthly Pipeline*.** Use the **Execute workflow**
button on the canvas of workflow `ITDS Monthly Pipeline`. It should finish green and post a question for each
material P&L line into `ClosingVariance QA`.

**2. Have the owners reply.** Each question is its own conversation —
answers must go in the thread, using **Reply** under the question, not as
a new message in the channel — a reply posted anywhere else is not picked
up. Plain natural language is fine and highly-recommended so that the agent can do its job of summarizing them. 

**3. Execute *Scanning for replies & Send commentary pipeline*.** Use the **Execute workflow**
button on the canvas of workflow `Scanning for replies & Send commentary pipeline`. It
collects the replies, summarises each one into the knowledge base, and
sends the commentary draft by email once every question has an answer.

That last email is the end of the run: the draft is what the pilot is
meant to produce, and Finance reviews it before anything is used.

If a question is left unanswered, the workflow posts a reminder in that
thread instead and no draft is sent — which is the intended behaviour, not
a failure. Answer the remaining ones and run step 3 again.
