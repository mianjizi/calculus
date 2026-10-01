/* 文本快照：把生成页里每套卷的前两题与页脚说明打成纯文本，肉眼核对 HTML 转义与排版。
   用法：node dump_text.mjs <html> */
import fs from 'node:fs';
import { JSDOM } from 'jsdom';

const html = fs.readFileSync(process.argv[2], 'utf8');
const w = new JSDOM(html, { runScripts: 'dangerously', pretendToBeVisual: true }).window;
const d = w.document;
const txt = (s) => s.replace(/\s+/g, ' ').trim();

console.log('标题:', txt(d.querySelector('.hdr').textContent));
console.log('副标题:', txt(d.querySelector('.sub').textContent));
for (const b of d.querySelectorAll('#tabs button')) {
  b.click();
  console.log('\n--- ' + txt(d.getElementById('pname').textContent));
  const qs = [...d.querySelectorAll('.q')].slice(0, 2);
  for (const q of qs) {
    console.log('  ' + txt(q.querySelector('div').textContent));
    const opts = [...q.querySelectorAll('.opt')].map((o) => txt(o.textContent));
    if (opts.length) console.log('    ' + opts.join(' | '));
    const inp = q.querySelector('input.ans');
    if (inp) console.log('    [填空框]');
    const rub = [...q.querySelectorAll('.rubric label')].map((l) => txt(l.textContent));
    if (rub.length) console.log('    得分点: ' + rub.join(' / '));
  }
}
console.log('\n页脚说明:');
for (const el of d.querySelectorAll('#notes .secTitle, #notes li')) console.log('  ' + txt(el.textContent));
console.log('\n含未转义尖括号的文本块:', [...d.querySelectorAll('.q')].filter((q) => q.innerHTML.includes('&lt;') === false && /[<>]/.test(q.textContent)).length);
