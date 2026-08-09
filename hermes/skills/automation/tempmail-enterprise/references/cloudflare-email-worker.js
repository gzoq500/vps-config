export default {
  async email(message) {
    const from = message.from;
    const to = message.to;
    const subject = message.headers.get("subject") || "(No subject)";
    const raw = await new Response(message.raw).text();
    const idx = raw.indexOf("\r\n\r\n");
    const text = idx !== -1 ? raw.substring(idx + 4).slice(-500) : raw.slice(-500);
    
    await fetch("https://tempmail.routerssh.web.id/api/incoming", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({from, to, subject, body: text, html: ""})
    });
  }
}
