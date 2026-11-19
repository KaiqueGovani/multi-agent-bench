// Text conversion only. Never parse response HTML or edit/send a message here.
(() => {
  const strong = /(?<![\\*])\*\*(?=\S)([^*\n]+?)(?<![\\\s])\*\*(?!\*)/g;
  const underscoreStrong = /(?<![\\_])__(?=\S)([^_\n]+?)(?<![\\\s])__(?!_)/g;
  const strike = /(?<![\\~])~~(?=\S)([^~\n]+?)(?<![\\\s])~~(?!~)/g;
  const combined = /(?<![\\*])\*\*\*(?=\S)([^*\n]+?)(?<![\\\s])\*\*\*(?!\*)/g;

  function emphasis(value, heading) {
    let output = value
      .replace(combined, (_, text) => heading ? text : `*_${text}_*`)
      .replace(strong, (_, text) => heading ? text : `*${text}*`)
      .replace(underscoreStrong, (_, text) => heading ? text : `*${text}*`)
      .replace(strike, (_, text) => `~${text}~`);
    // The whole heading will be bold. Avoid nesting the same WhatsApp marker.
    if (heading) output = output.replace(/(?<![\\*])\*(?=\S)([^*\n]*?\S)(?<!\\)\*(?!\*)/g, "$1");
    return output;
  }

  function closing(value, start, open, close) {
    let depth = 1;
    for (let index = start + 1; index < value.length; index++) {
      if (value[index] === "\\") { index++; continue; }
      if (value[index] === open) depth++;
      else if (value[index] === close && --depth === 0) return index;
    }
    return -1;
  }

  function links(value, heading) {
    let output = "", cursor = 0;
    for (let index = 0; index < value.length; index++) {
      if (value[index] === "\\") { index++; continue; }
      if (value[index] !== "[" || value[index - 1] === "!") continue;
      const labelEnd = closing(value, index, "[", "]");
      if (labelEnd < 0 || value[labelEnd + 1] !== "(") continue;
      const targetEnd = closing(value, labelEnd + 1, "(", ")");
      if (targetEnd < 0) continue;
      const target = value.slice(labelEnd + 2, targetEnd).trim();
      const match = target.match(/^(?:<([^<>\s]+)>|([^\s]+?))(?:\s+(?:"[^"\n]*"|'[^'\n]*'|\([^\n]*\)))?$/);
      const url = match?.[1] || match?.[2];
      // Unknown/relative destinations stay literal instead of guessing a URL.
      if (!url || !/^(?:https?:\/\/|mailto:|tel:)/i.test(url)) continue;
      const label = emphasis(value.slice(index + 1, labelEnd), heading);
      output += emphasis(value.slice(cursor, index), heading);
      output += label && label !== url ? `${label} (${url})` : url;
      cursor = targetEnd + 1;
      index = targetEnd;
    }
    return output + emphasis(value.slice(cursor), heading);
  }

  function inline(value, heading = false) {
    let output = "", cursor = 0;
    // Code spans are copied verbatim, including any Markdown-looking content.
    for (let index = 0; index < value.length; index++) {
      if (value[index] === "\\") { index++; continue; }
      if (value[index] !== "`") continue;
      let runEnd = index + 1;
      while (value[runEnd] === "`") runEnd++;
      const marker = value.slice(index, runEnd);
      let end = value.indexOf(marker, runEnd);
      while (end >= 0 && (value[end - 1] === "`" || value[end + marker.length] === "`")) end = value.indexOf(marker, end + marker.length);
      if (end < 0) end = value.length - marker.length;
      const after = Math.max(runEnd, end + marker.length);
      output += links(value.slice(cursor, index), heading) + value.slice(index, after);
      cursor = after;
      index = after - 1;
    }
    return output + links(value.slice(cursor), heading);
  }

  function convertOnce(text) {
    const lines = text.split("\n");
    let fence = null;
    return lines.map((line) => {
      if (fence) {
        const match = line.match(/^\s*(`{3,}|~{3,})\s*$/);
        if (match && match[1][0] === fence.character && match[1].length >= fence.length) fence = null;
        return line;
      }
      const opener = line.match(/^ {0,3}(`{3,}|~{3,})([^`~]*)$/);
      if (opener) { fence = { character: opener[1][0], length: opener[1].length }; return line; }
      // Indented code is literal too. A tab/four spaces must not turn code
      // examples containing ** or links into response formatting.
      if (/^(?: {4}|\t)/.test(line)) return line;
      const heading = line.match(/^( {0,3})#{1,6}[\t ]+(.+?)(?:[\t ]+#+)?[\t ]*$/);
      if (heading) return `${heading[1]}*${inline(heading[2], true)}*`;
      return inline(line);
    }).join("\n");
  }

  function toWhatsApp(text) {
    const original = String(text ?? "").replace(/\r\n?/g, "\n");
    const result = convertOnce(original);
    // Adjacent or ambiguous delimiters can create a second interpretation
    // after conversion. Keep those inputs literal instead of reinterpreting
    // an already converted WhatsApp reply or changing it on every click.
    return convertOnce(result) === result ? result : original;
  }

  globalThis.MabWhatsAppFormatter = { toWhatsApp };
})();
