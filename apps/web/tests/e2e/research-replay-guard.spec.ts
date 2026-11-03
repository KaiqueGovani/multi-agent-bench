import { expect, test, type APIResponse } from "@playwright/test";

const enabled = process.env.MAB_ENABLE_PRIVATE_REPLAY === "1";

async function expectHidden(response: APIResponse) {
  expect(response.status()).toBe(404);
  expect(response.headers()["cache-control"]).toBe("no-store");
  expect(response.headers()["x-mab-mode"]).toBeUndefined();
  expect(await response.json()).toEqual({ error: "Não encontrado." });
}

test("mantém o replay privado fechado por padrão", async ({ request }) => {
  test.skip(enabled, "Requer o servidor com replay desabilitado.");
  await expectHidden(await request.get("/api/research"));
  await expectHidden(await request.get("/api/research?run=indisponivel"));
});

test("oculta o replay de requisições encaminhadas ou de outra origem", async ({ request }) => {
  test.skip(!enabled, "Requer o servidor com replay explicitamente habilitado.");
  const externalHeaders: Record<string, string>[] = [
    { Host: "example.invalid" },
    { "X-Forwarded-Host": "example.invalid" },
    { "X-Forwarded-For": "203.0.113.24" },
    { Forwarded: "for=203.0.113.24" },
    { Origin: "https://example.invalid" },
    { "Sec-Fetch-Site": "cross-site" },
  ];
  for (const headers of externalHeaders) {
    await expectHidden(await request.get("/api/research", { headers }));
  }
});
