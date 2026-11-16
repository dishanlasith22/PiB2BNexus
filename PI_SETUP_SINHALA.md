# PIB2BNexus Pi Sign In + Payment setup

## What was changed
- Replaced the old `components.html()` login (which cannot return a value to Python) with a bidirectional Streamlit component.
- Pi SDK login now sends the access token to the FastAPI backend.
- Backend verifies the token against Pi `GET /v2/me`; only verified UID/username are returned.
- Added server-side Pi payment approval and completion endpoints.
- Removed the false customer-side "payment successful" message that did not call Pi.
- Removed `pi-app-validation.txt` from this package because it contained a credential-like value. Rotate/revoke that value in the Pi Developer Portal if it was an active credential.

## Deploy
1. Upload these changed files to GitHub (do not upload secrets).
2. Keep the existing Render Streamlit service. Its start command remains your existing Streamlit command.
3. Create a SECOND Render Web Service from the same repository for FastAPI:
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn pi_backend:app --host 0.0.0.0 --port $PORT`
4. On the FastAPI service set `PI_API_KEY` to your Pi Server API Key.
5. On both services set `PI_SANDBOX=true` initially. Configure the same `PI_PAYMENT_AMOUNT` and `PI_PAYMENT_MEMO` on both services. Start with a small Sandbox test amount only.
6. On the Streamlit service set `PI_BACKEND_URL` to the FastAPI Render URL.
7. Open the app inside Pi Browser, test sign-in, then test a Sandbox payment.
8. Switch to production only after checking the Pi Developer Portal app configuration and production access.

## Important boundaries
- The payment button is a fixed-amount demo integration test. It is not yet tied to the existing QR bill / POS order / inventory / shop_sales workflow.
- Do not claim a sale is paid or deliver stock based only on the browser callback. Only fulfill after backend Pi completion is confirmed and the verified payment is stored against a server-created order.
- Before production, implement Supabase payment/order persistence, unique constraints/idempotency, incomplete-payment reconciliation, order ownership checks, and proper RLS. The supplied database schema screenshot did not show a payments table, and table columns/constraints were not available.
- Existing project includes other demo/fallback behaviours; this Pi patch does not certify the entire POS as production-ready.
- Never expose the Pi Server API Key. The token is held in Streamlit server session state for this initial integration; consider server-side session cookies for a hardened deployment.

## Official Pi docs
- Authentication: https://developers.minepi.com/docs/authenticate-user/Authentication
- Payments: https://developers.minepi.com/docs/accept-payment/Payments
- Platform API: https://developers.minepi.com/docs/api-reference/PlatformAPI
- SDK reference: https://developers.minepi.com/docs/api-reference/SdkReference


## Pi Authentication update (App Studio login exchange)

The current code now sends only the Pi SDK `accessToken` to the FastAPI backend at `/auth/login`. The backend exchanges it with Pi App Studio at `https://backend.appstudio-u7cm9zhmha0ruwv8.piappengine.com/pi/auth/v1/login`, trusts only the returned `user.uid` and `user.username`, and issues a short-lived signed app session. Browser-supplied uid/username are not accepted. The App Studio `sessionToken` is not exposed to the browser.

Render backend environment variables:
- `PI_SESSION_SECRET`: random secret, at least 32 characters (required for app login). Generate a new unique secret and keep it private.
- `PI_API_KEY`: needed only if Pi payments are enabled; not used for sign-in.
- `PI_SANDBOX`: keep `true` while testing in Pi Sandbox. SDK sandbox flag is intentionally not passed to `Pi.init`; the SDK detects its environment.
- `PI_PAYMENT_AMOUNT` and `PI_PAYMENT_MEMO`: payment test configuration only.

Streamlit service:
- `PI_BACKEND_URL=https://pib2bnexus-pi-backend.onrender.com` (use your actual backend hostname).

After adding `PI_SESSION_SECRET`, redeploy the FastAPI backend and Streamlit service. Authentication must be tested in the registered Pi Sandbox app using its development URL; ordinary desktop Chrome is not a valid Pi sign-in test. This package has not been live-verified in Pi Sandbox.
