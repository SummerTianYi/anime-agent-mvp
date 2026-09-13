import assert from "node:assert/strict";
import test from "node:test";
import {createDriveAuth} from "./oauth.mjs";

class FakeOAuth {
    constructor(...args) { this.args = args; }
    setCredentials(credentials) { this.credentials = credentials; }
}
const google = {auth:{OAuth2:FakeOAuth}};
const keys = {client_id:"synthetic-client", client_secret:"synthetic-secret"};
test("installed application supplies refresh identity", () => {
    const input = Object.freeze({refresh_token:"synthetic-refresh",expiry_date:1});
    const auth = createDriveAuth(google,{installed:keys},input);
    assert.deepEqual(auth.args,[keys.client_id,keys.client_secret]);
    assert.deepEqual(auth.credentials,input);
    assert.notEqual(auth.credentials,input);
});
test("web application supported without widening scopes", () => {
    const auth = createDriveAuth(google,{web:keys},{access_token:"synthetic",scope:"readonly"});
    assert.equal(auth.credentials.scope,"readonly");
});
test("missing application identity fails before any network", () => {
    for (const config of [null,{}, {installed:{client_id:"x"}}]) {
        assert.throws(()=>createDriveAuth(google,config,{refresh_token:"synthetic"}),/application/);
    }
});
test("missing credentials fail before any network", () => {
    for (const credentials of [null,{}, "secret"]) {
        assert.throws(()=>createDriveAuth(google,{installed:keys},credentials),/credentials/);
    }
});
