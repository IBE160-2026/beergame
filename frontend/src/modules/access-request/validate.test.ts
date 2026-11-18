import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import { cleanAccessRequest, validateAccessRequest } from "./validate";

const errors = nb.accessRequest.errors;
const OK = { name: "Ola Nordmann", email: "ola@usn.no", institution: "USN" };

describe("«Be om lærertilgang» checks", () => {
  it("passes a complete request", () => {
    expect(validateAccessRequest(OK)).toEqual({});
  });

  it("names each empty field", () => {
    expect(validateAccessRequest({ name: "  ", email: "", institution: " " })).toEqual({
      name: errors.nameEmpty,
      email: errors.emailEmpty,
      institution: errors.institutionEmpty,
    });
  });

  it("refuses names over 200 characters, counted as characters", () => {
    expect(validateAccessRequest({ ...OK, name: "ø".repeat(200) })).toEqual({});
    expect(validateAccessRequest({ ...OK, name: "ø".repeat(201) }).name).toBe(errors.nameLong);
    expect(validateAccessRequest({ ...OK, institution: "x".repeat(201) }).institution).toBe(errors.institutionLong);
  });

  it("uses the address reasons of «Logg inn» and the Institution rule", () => {
    expect(validateAccessRequest({ ...OK, email: "ola.usn.no" }).email).toBe(nb.auth.login.errors.emailNoAt);
    expect(validateAccessRequest({ ...OK, institution: "a@b" }).institution).toBe(errors.institutionInvalid);
  });

  it("sends the names cleaned and the address trimmed", () => {
    expect(cleanAccessRequest({ name: " Ola   N ", email: " ola@usn.no ", institution: " USN  Bø " })).toEqual({
      name: "Ola N",
      email: "ola@usn.no",
      institution: "USN Bø",
    });
  });
});
