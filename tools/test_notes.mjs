/* 复习讲义.html 的端到端测试（jsdom）。
   用法： node test_notes.mjs <复习讲义.html> <bank.json>
   退出码 0 表示全部断言通过。 */
import fs from 'node:fs';
import { JSDOM } from 'jsdom';

const [htmlPath, bankPath] = process.argv.slice(2);
const html = fs.readFileSync(htmlPath, 'utf8');
const bank = JSON.parse(fs.readFileSync(bankPath, 'utf8'));
const dom = new JSDOM(html, { runScripts: 'dangerously', pretendToBeVisual: true });
const w = dom.window;
const d = w.document;

let pass = 0, fail = 0;
const ok = (name, cond, extra = '') => {
  if (cond) { pass++; console.log('  ✓ ' + name); }
  else { fail++; console.log('  ✗ ' + name + (extra ? '  → ' + extra : '')); }
};
const q = (s) => d.querySelectorAll(s);
const topics = () => [...q('.topic')].filter(t => (t.dataset.tid || '').trim());

console.log('复习讲义.html 端到端测试');

// 1. 结构
ok('章节 9 个（前言 + 4 章 + 4 附录）', q('section.chapter').length === 9,
   '实际 ' + q('section.chapter').length);
ok('考点 29 个', topics().length === 29, '实际 ' + topics().length);
ok('每个考点都有标题与正文', topics().every(t =>
   t.querySelector('h2.thead') && t.querySelector('.tbody')));
ok('考点正文非空（>120 字）', topics().every(t =>
   t.querySelector('.tbody').textContent.trim().length > 120));

// 2. 目录锚点全部可跳
const links = [...q('#toc a[href^="#"]')];
const dead = links.filter(a => !d.getElementById(decodeURIComponent(a.getAttribute('href').slice(1))));
ok('目录链接 ' + links.length + ' 条全部有对应锚点', dead.length === 0,
   dead.map(a => a.getAttribute('href')).join(','));

// 3. 附录 A 逐题索引与题库一致
const rows = [...q('table')].flatMap(t => [...t.querySelectorAll('tr')])
  .filter(tr => /^套\d+ 第\d+题$/.test((tr.cells[0]?.textContent || '').trim()));
const expect = [];
for (let i = 1; i <= bank.papers.length; i++) {
  for (const qq of bank.papers[i - 1].qs) expect.push(`套${i} 第${qq.n}题`);
}
ok('逐题索引 80 行', rows.length === 80, '实际 ' + rows.length);
ok('索引题号与题库逐一对应', rows.map(r => r.cells[0].textContent.trim()).join('|') === expect.join('|'));
const noTid = rows.filter(r => r.cells[2].textContent.includes('—'));
ok('每道题都归入了考点', noTid.length === 0, noTid.length + ' 行未归类');
const answersOk = rows.every(r => (r.cells[3].textContent || '').trim().length > 0);
ok('索引每行都有参考答案/判分方式', answersOk);

// 4. 折叠交互
const firstTopic = topics()[0];
ok('默认折叠', firstTopic.classList.contains('closed'));
firstTopic.querySelector('h2.thead').dispatchEvent(new w.Event('click', { bubbles: true }));
ok('点标题展开', !firstTopic.classList.contains('closed'));
firstTopic.querySelector('h2.thead').dispatchEvent(new w.Event('click', { bubbles: true }));
ok('再点收起', firstTopic.classList.contains('closed'));
d.getElementById('bOpen').dispatchEvent(new w.Event('click', { bubbles: true }));
ok('「展开全部」后无折叠', topics().every(t => !t.classList.contains('closed')));
d.getElementById('bShut').dispatchEvent(new w.Event('click', { bubbles: true }));
ok('「收起考点」后全折叠', topics().every(t => t.classList.contains('closed')));

// 5. 搜索过滤
const inp = d.getElementById('q');
const search = (s) => {
  inp.value = s;
  inp.dispatchEvent(new w.Event('input', { bubbles: true }));
  return topics().filter(t => !t.classList.contains('hide'));
};
let hits = search('罗尔');
ok('搜索「罗尔」命中且命中项都含关键词', hits.length > 0 && hits.every(t => t.textContent.includes('罗尔')),
   hits.length + ' 个');
hits = search('分部积分');
ok('搜索「分部积分」命中', hits.length > 0 && hits.every(t => t.textContent.includes('分部积分')), hits.length + ' 个');
hits = search('zzz不存在的词');
ok('搜索无结果时全部隐藏', hits.length === 0);
hits = search('');
ok('清空搜索后恢复 29 个', hits.length === 29, '实际 ' + hits.length);
ok('计数文字正确', d.getElementById('cnt').textContent.includes('29'), d.getElementById('cnt').textContent);

// 6. 无 markdown 残留
const txt = d.body.textContent;
ok("无未渲染的 markdown（** 与 | ---）", !txt.includes('**') && !txt.includes('| ---'));
ok('无 HTML 注释泄漏到正文', !txt.includes('<!--') && !txt.includes('BEGIN:INDEX'));
const raw = d.body.innerHTML;
ok('表格已渲染成 <table>', raw.includes('<table>') && raw.includes('<th'));
ok('blockquote 已渲染', raw.includes('<blockquote>'));

// 7. 关键内容抽查
ok('含「辅助函数」清单表', txt.includes('e^{λx}f(x)') || txt.includes('e^(λx)f(x)'));
ok('含易错清单 25 条', ['加减位置', '法线', '铅直渐近线', '+ C'].every(s => txt.includes(s)));
ok('引用外部自测页', /(自测|quiz)\.html/.test(raw));

// 8. 加料块：原理 / 名师方法 / 出处 / 例题
const blocks = (t, label) => t.textContent.includes(label);
ok('每个考点都有「原理」', topics().every(t => blocks(t, '原理（为什么这招成立）')));
ok('每个考点都有「名师方法」', topics().every(t => blocks(t, '名师方法')));
ok('每个考点都有「出处」清单', topics().every(t => blocks(t, '出处')));
ok('每个考点都有「例题」', topics().every(t => blocks(t, '例题')));
const withLink = topics().filter(t => [...t.querySelectorAll('a[href^="http"]')].length > 0);
ok('每个考点都带可点开的出处链接', withLink.length === 29, '只有 ' + withLink.length + ' 个');
const linkCount = [...q('a[href^="http"]')].length;
ok('全页外链不少于 89 条', linkCount >= 89, '实际 ' + linkCount);
const methodRows = [...q('table')].flatMap(t => [...t.querySelectorAll('tr')])
  .filter(tr => /^\d+\.\d+\s/.test((tr.cells[0]?.textContent || '').trim()));
ok('附录 D 名师方法 89 行', methodRows.length === 89, '实际 ' + methodRows.length);
ok('附录 D 每行都有出处链接', methodRows.every(tr => tr.querySelector('a[href^="http"]')));
ok('附录 D 每行都有老师与要点', methodRows.every(tr =>
   (tr.cells[1].textContent || '').trim() && (tr.cells[3].textContent || '').trim().length > 8));
ok('名师方法里出现张宇与武忠祥', txt.includes('张宇｜') && txt.includes('武忠祥｜'));
hits = search('张宇');
ok('搜索「张宇」能命中考点', hits.length > 5, hits.length + ' 个');
hits = search('');
ok('清空搜索后仍为 29 个', hits.length === 29, '实际 ' + hits.length);

console.log(`\n通过 ${pass} 项，失败 ${fail} 项`);
process.exit(fail ? 1 : 0);
