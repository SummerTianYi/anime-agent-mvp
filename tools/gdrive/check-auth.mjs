// Explicit operator diagnostic only: authentication, no files/list/search.
import fs from "node:fs";
import {google} from "googleapis";
import {createDriveAuth} from "./oauth.mjs";
try {
    const config = JSON.parse(fs.readFileSync(process.env.GDRIVE_OAUTH_PATH,"utf8"));
    const credentials = JSON.parse(fs.readFileSync(process.env.GDRIVE_CREDENTIALS_PATH,"utf8"));
    const auth = createDriveAuth(google,config,credentials);
    auth.transporter.defaults = {...auth.transporter.defaults,timeout:15000,retry:false};
    const {token} = await auth.getAccessToken();
    const info = await auth.getTokenInfo(token);
    const ok = info.scopes.includes("https://www.googleapis.com/auth/drive.readonly");
    console.log(JSON.stringify({authenticated:ok,contentReads:0,credentialWrites:0}));
    process.exitCode = ok ? 0 : 1;
} catch {
    console.log(JSON.stringify({authenticated:false,contentReads:0,credentialWrites:0}));
    process.exitCode = 1;
}
