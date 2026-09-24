# Deploy on Koyeb + Supabase

This project deploys as one Docker web service: the FastAPI server serves the
website and API from the same URL. Koyeb runs the service and Supabase stores
the PostgreSQL data.

## 1. Publish the project to GitHub

Create a new **private** GitHub repository, then publish this folder to it.
Keep the repository private because it contains the application source, even
though the eventual website has its own shared-password screen.

## 2. Create the free Supabase database

1. Create a Supabase account and select **New project**.
2. Give the project a name such as `cre-price-solver`, choose a region near you,
   and save the database password in a password manager.
3. Once the database is ready, select **Connect**.
4. Copy the **Session pooler** connection string. This is the right connection
   method for Koyeb because it works over IPv4. Paste it into Koyeb exactly as
   copied; the application automatically selects its PostgreSQL driver and
   enforces TLS for Supabase.

The copied connection string is a secret. Do not paste it into GitHub or send
it in chat.

## 3. Create the free Koyeb web service

1. Create a Koyeb account and connect GitHub when prompted.
2. Select **Create App**, choose the GitHub repository, and use the `Dockerfile`
   at the repository root as the build method.
3. Select the **Free Instance**, then choose either Washington, D.C. or
   Frankfurt—the regions available on Koyeb's free tier.
4. Expose port **8000** as **HTTP**, with route `/`.
5. Add these environment variables in the Koyeb dashboard. Mark the first three
   values as secrets:

   | Name | Value |
   | --- | --- |
   | `DATABASE_URL` | The Supabase Session pooler connection string |
   | `APP_ACCESS_PASSWORD` | The shared password people will enter at the website |
   | `APP_SESSION_SECRET` | A separate random secret; never reuse the password |
   | `APP_REQUIRE_AUTH` | `true` |
   | `APP_SESSION_COOKIE_SECURE` | `true` |

6. Click **Deploy**. Koyeb builds the image, applies the tracked database
   migration, then gives the service a `koyeb.app` URL.

## 4. Verify the live site

Open the Koyeb URL. You should see the password screen. On your computer, run:

```powershell
cd backend
$env:SMOKE_TEST_PASSWORD = "your shared website password"
uv run python scripts/smoke_test.py https://your-koyeb-url.koyeb.app
```

The test validates protected access, the web page, the health endpoint, and a
known underwriting calculation without adding a deal to the database.

## Updating the website

After Koyeb is connected to GitHub, push changes to the selected branch. Koyeb
rebuilds and redeploys automatically. The free service goes to sleep after one
hour with no traffic and wakes when visited; the first request after sleeping
can take longer than normal.
