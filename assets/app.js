(() => {
  'use strict';
  let report = JSON.parse(document.getElementById('report-data').textContent);
  const settings = JSON.parse(document.getElementById('client-settings').textContent);
  const app = document.getElementById('app');
  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[char]));
  const num = value => new Intl.NumberFormat('en-US').format(value || 0);
  const hour = value => value == null ? 'Not enough dated activity' : `${String(value).padStart(2, '0')}:00`;
  const dateLabel = value => value ? new Date(`${value}T00:00:00Z`).toLocaleDateString('en-US', {month:'short', day:'numeric', year:'numeric', timeZone:'UTC'}) : 'No dated messages';
  const localZone = () => {
    try { return Intl.DateTimeFormat().resolvedOptions().timeZone || null; }
    catch { return null; }
  };
  let statusTimer;
  function status(message) {
    document.getElementById('status').textContent = message;
    clearTimeout(statusTimer);
    statusTimer = setTimeout(() => { document.getElementById('status').textContent = ''; }, 6000);
  }

  function header(hasReport) {
    const shared = report?.shared;
    return `<header class="topbar"><div class="shell topbar-inner"><a class="wordmark" href="#main">mirror.<span>for OpenCode</span></a>
      <div class="top-actions"><span class="local-label">${shared ? 'Shared snapshot' : 'Local & read-only'}</span>
      ${hasReport ? '<button class="secondary" data-action="card">Save share card</button>' : ''}</div></div></header>`;
  }

  function archiveForm(id) {
    return `<form id="${id}" class="archive-form"><label for="${id}-path">Path to your opencode.db</label><input id="${id}-path" name="path" type="text" placeholder="~/.local/share/opencode/opencode.db" autocomplete="off" spellcheck="false" required>
      <p class="form-help">Read directly on this computer. Your database is never uploaded. Activity uses ${settings.timezoneAuto ? 'your browser’s local timezone' : 'the timezone selected with --timezone'}.</p>
      <button type="submit">Find my mirror <span aria-hidden="true">↗</span></button><p class="form-error" role="alert" hidden></p></form>`;
  }

  function renderWelcome() {
    app.innerHTML = `${header(false)}<main class="shell welcome" id="main"><p class="eyebrow">Your work, reflected.</p><h1>Meet yourself<br>in your work.</h1>
      <p class="lead">The questions you ask. The way you move work forward. The hours you return to. Your OpenCode archive has a story to tell.</p>
      ${archiveForm('welcome-form')}<div class="welcome-points"><div><h3>Recognize your style.</h3><p>A working persona and communication fingerprint, with the evidence behind them.</p></div>
      <div><h3>Find your rhythm.</h3><p>A weekday-and-hour mosaic of when your conversations gather, in your local time.</p></div><div><h3>Keep a reflection.</h3><p>A visual share card or an offline report, ready to save and share.</p></div></div></main>`;
    bindForms();
  }

  function fingerprint() {
    const strongest = Math.max(...report.communication.signals.map(row => row.rate));
    return `<aside class="fingerprint" aria-labelledby="fingerprint-title"><div class="fingerprint-top"><h2 id="fingerprint-title">Your conversation fingerprint</h2><span>Share of messages · 0–100%</span></div>
      ${report.communication.signals.map((signal, index) => `<div class="signal ${strongest > 0 && signal.rate === strongest && index === report.communication.signals.findIndex(row => row.rate === strongest) ? 'best' : ''}">
      <div class="signal-label"><span>${esc(signal.label)}</span><span><b>${signal.rate.toFixed(1)}%</b> · ${num(signal.count)} / ${num(report.summary.messages)}</span></div>
      <div class="track" role="img" aria-label="${esc(signal.label)}: ${signal.rate}% of filtered messages"><i style="width:${signal.rate}%"></i></div></div>`).join('')}
      <p class="method">Patterns in ${num(report.summary.messages)} filtered root user messages. Categories overlap. These are language signals, not personality scores or population percentiles.</p>
      <details><summary>Why this working persona?</summary><p>${esc(report.assessment.persona_rules)}</p><p>${esc(report.assessment.method)}</p><p>${esc(report.methods.human)} ${num(report.methods.copied_human_messages_removed)} identifiable message copies removed.</p></details></aside>`;
  }

  function heatmap() {
    const matrix = report.rhythm.heatmap;
    const max = Math.max(0, ...matrix.flat());
    if (!max) return '<div class="empty-chart">No dated root user messages yet. Your rhythm will appear as the archive grows.</div>';
    return `<div class="chart-scroll" tabindex="0" role="region" aria-label="Weekly activity chart; scroll horizontally on narrow screens"><div class="heat-chart" role="img" aria-label="Filtered messages by weekday and hour in ${esc(report.timezone)}. Peak hour ${hour(report.rhythm.peak_hour)}, busiest weekday ${days[report.rhythm.peak_weekday]}.">
      ${matrix.map((row, day) => `<div class="heat-row"><span class="heat-label">${days[day].slice(0,3)}</span>${row.map((value, h) => `<span class="heat-cell ${value === max ? 'peak' : ''}" title="${days[day]}, ${hour(h)}–${hour((h+1)%24)}: ${num(value)} messages"><i style="width:${Math.sqrt(value/max)*100}%;height:${Math.sqrt(value/max)*100}%"></i></span>`).join('')}</div>`).join('')}
      <div class="heat-hours"><span></span>${Array.from({length:24}, (_, h) => `<span>${h % 4 === 0 || h === 23 ? String(h).padStart(2,'0') : ''}</span>`).join('')}</div></div></div>`;
  }

  function rhythmTable() {
    return `<details><summary>Exact weekday and hour counts</summary><div class="data-table" tabindex="0" role="region" aria-label="Exact activity table"><table><caption>Filtered messages · ${esc(report.timezone)}</caption><thead><tr><th scope="col">Hour</th>${days.map(day => `<th scope="col">${day.slice(0,3)}</th>`).join('')}</tr></thead><tbody>
      ${Array.from({length:24}, (_, h) => `<tr><th scope="row">${hour(h)}</th>${days.map((_,day) => `<td>${num(report.rhythm.heatmap[day][h])}</td>`).join('')}</tr>`).join('')}</tbody></table></div><p class="method">Filtered root user message creation times in ${esc(report.timezone)}, including that zone’s daylight saving rules for each date. Activity is archived interaction, not labor hours.</p></details>`;
  }

  function renderReport() {
    const coverage = `${dateLabel(report.coverage.start)} — ${dateLabel(report.coverage.end)}`;
    const canSwitch = !report.shared && location.protocol !== 'file:';
    app.innerHTML = `${header(true)}<main id="main" class="shell"><section class="hero" aria-labelledby="persona"><div><p class="eyebrow">Your working-style mirror ${report.assessment.sample==='early' ? '· early sketch' : ''}</p>
      <h1 id="persona">${esc(report.assessment.persona.replace(/^The /,''))}.</h1><p class="description">${esc(report.assessment.description)}</p>
      <div class="signature"><span class="quiet">How you communicate</span><strong>${esc(report.assessment.communication)}</strong></div>
      ${report.assessment.secondary ? `<p class="small quiet" style="margin-top:12px">With a secondary ${esc(report.assessment.secondary.replace(/^The /,'').toLowerCase())} streak.</p>` : ''}
      <div class="hero-actions"><a class="button" href="#rhythm">Explore my rhythm <span aria-hidden="true">↓</span></a><button class="secondary" data-action="export">Export report</button>${canSwitch ? '<button class="text-button" data-action="archive">Open another archive</button>' : ''}</div>
      <p class="hero-note">A lens on your archived habits, not a fixed identity.<br>${coverage} · ${esc(report.timezone)}</p></div>${fingerprint()}</section>
      <section class="section" id="rhythm"><div class="section-header"><div><p class="section-number">Your rhythm</p><h2>You have a rhythm.</h2><p>Every square is a weekday and hour. See where the conversations tend to gather.</p></div><span class="small quiet">${esc(report.timezone)}</span></div>
      <p class="mobile-hint">Swipe horizontally to explore all 24 hours.</p>${heatmap()}<div class="chart-caption"><span>Square area ∝ filtered message count. Blank = zero.</span><span>Orange marks the highest weekday/hour count.</span></div>
      ${rhythmTable()}</section></main>
      ${canSwitch ? `<dialog id="archive-dialog" aria-labelledby="archive-title"><div class="dialog-head"><h2 id="archive-title" style="font-size:1.6rem">Open another mirror.</h2><button id="close-dialog" aria-label="Close archive dialog">×</button></div>${archiveForm('switch-form')}</dialog>` : ''}`;
    if (canSwitch) {
      document.getElementById('close-dialog').addEventListener('click',()=>document.getElementById('archive-dialog').close());
      bindForms();
    }
  }

  function bindForms() {
    document.querySelectorAll('.archive-form').forEach(form=>form.addEventListener('submit',async event=>{
      event.preventDefault();
      const button = form.querySelector('button[type="submit"]');
      const input = form.querySelector('input');
      const error = form.querySelector('.form-error');
      error.hidden = true;
      input.removeAttribute('aria-invalid');
      button.disabled = true;
      button.textContent = 'Reading your archive…';
      form.setAttribute('aria-busy','true');
      try {
        const response = await fetch('/api/analyze', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({path:input.value, ...(settings.timezoneAuto && localZone() ? {timezone:localZone()} : {})})});
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'This archive could not be read.');
        report = data;
        document.getElementById('report-data').textContent = JSON.stringify(report);
        location.hash='main';
        renderCurrent();
        window.scrollTo({top:0,behavior:'instant'});
        document.getElementById('persona').setAttribute('tabindex','-1');
        document.getElementById('persona').focus({preventScroll:true});
        status('Your mirror is ready.');
      } catch (exception) {
        error.textContent = exception.message;
        error.hidden = false;
        input.setAttribute('aria-invalid','true');
        button.disabled = false;
        button.textContent = 'Find my mirror ↗';
        input.focus();
      } finally { form.removeAttribute('aria-busy'); }
    }));
  }

  function download(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url; link.download = filename;
    document.body.append(link); link.click(); link.remove();
    setTimeout(()=>URL.revokeObjectURL(url),10000);
  }

  function exportHTML() {
    const shared = JSON.parse(JSON.stringify(report));
    shared.shared = true;
    shared.projects.forEach((project,index)=>{project.name=`Project ${String(index+1).padStart(2,'0')}`;});
    const root = document.documentElement.cloneNode(true);
    // Clear the rendered local DOM as well as anonymizing the embedded data.
    root.querySelector('#app').innerHTML = '';
    root.querySelector('#status').textContent = '';
    root.querySelector('#client-settings').textContent = JSON.stringify({timezoneAuto:false});
    root.querySelector('#report-data').textContent = JSON.stringify(shared).replace(/</g,'\\u003c').replace(/>/g,'\\u003e').replace(/&/g,'\\u0026');
    download(new Blob(['<!doctype html>\n',root.outerHTML],{type:'text/html;charset=utf-8'}),'opencode-mirror.html');
    status('Exported an offline snapshot of your style and rhythm.');
  }

  function cardSVG() {
    const style = getComputedStyle(document.documentElement);
    const color = role=>style.getPropertyValue(`--${role}`).trim();
    const ink=color('text-primary'), slate=color('structure'), paper=color('canvas'), orange=color('emphasis');
    const quiet=color('text-secondary');
    const bodyFont=style.getPropertyValue('--font-body').trim();
    const fontCSS=document.getElementById('mirror-fonts').textContent;
    const type=Object.fromEntries(['wordmark','title','body','section','label','value','caption'].map(role=>[role,parseFloat(style.getPropertyValue(`--card-${role}`))]));
    const markStyle=getComputedStyle(document.querySelector('.wordmark'));
    const taglineStyle=getComputedStyle(document.querySelector('.wordmark span'));
    const headingStyle=getComputedStyle(document.querySelector('#persona'));
    const headingTracking=parseFloat(headingStyle.letterSpacing)/parseFloat(headingStyle.fontSize);
    const markScale=type.wordmark/parseFloat(markStyle.fontSize);
    const markSpacing=parseFloat(markStyle.letterSpacing)*markScale;
    const taglineSize=parseFloat(taglineStyle.fontSize)*markScale;
    const taglineSpacing=parseFloat(taglineStyle.letterSpacing)*markScale;
    const title=report.assessment.persona.replace(/^The /,'');
    const context=document.createElement('canvas').getContext('2d');
    context.font=`${type.body}px ${bodyFont}`;
    const description=[''];
    for(const word of report.assessment.description.split(' ')) {
      const line=(description.at(-1)+' '+word).trim();
      if(context.measureText(line).width>1056 && description.at(-1)) description.push(word);
      else description[description.length-1]=line;
    }
    const strongest=Math.max(...report.communication.signals.map(row=>row.rate));
    const strongestIndex=strongest>0 ? report.communication.signals.findIndex(row=>row.rate===strongest) : -1;
    const rhythmMax=Math.max(0,...report.rhythm.heatmap.flat());
    const coverage=report.coverage.start ? `${dateLabel(report.coverage.start)} — ${dateLabel(report.coverage.end)}` : 'No dated messages';
    return `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1200" viewBox="0 0 1200 1200" role="img" aria-labelledby="card-title card-desc"><title id="card-title">OpenCode Mirror: ${esc(title)}</title><desc id="card-desc">Working-style snapshot. Rates are shares of ${num(report.summary.messages)} filtered messages; categories overlap. The weekday/hour mosaic uses ${esc(report.timezone)}. A working lens, not a fixed identity.</desc><defs><style><![CDATA[${fontCSS} text{font-family:${bodyFont};font-variant-numeric:tabular-nums} .display{font-family:${headingStyle.fontFamily};font-weight:${headingStyle.fontWeight};letter-spacing:${headingTracking}em} .wordmark{font-family:${markStyle.fontFamily};font-weight:${markStyle.fontWeight};letter-spacing:${markSpacing}px} .tagline{font-family:${taglineStyle.fontFamily};font-weight:${taglineStyle.fontWeight};letter-spacing:${taglineSpacing}px}]]></style></defs>
      <rect width="1200" height="1200" fill="${paper}"/><text class="wordmark" x="72" y="80" fill="${ink}" font-size="${type.wordmark}">mirror.</text><text class="tagline" x="72" y="118" fill="${quiet}" font-size="${taglineSize}">FOR OPENCODE</text>
      <text class="display" x="72" y="220" fill="${ink}" font-size="${type.title}">${esc(title)}.</text>
      ${description.map((line,index)=>`<text x="72" y="${260+index*38}" fill="${quiet}" font-size="${type.body}">${esc(line)}</text>`).join('')}
      <text x="72" y="346" fill="${ink}" font-size="${type.label}" font-weight="600">${esc(report.assessment.communication)}</text><line x1="72" x2="1128" y1="374" y2="374" stroke="${slate}" stroke-opacity=".22" stroke-width="1"/>
      ${report.communication.signals.map((row,index)=>{const y=420+index*44;return `<text x="72" y="${y}" fill="${ink}" font-size="${type.label}">${esc(row.label)}</text><rect x="500" y="${y-21}" width="440" height="16" rx="4" fill="${slate}" fill-opacity=".12"/><rect x="500" y="${y-21}" width="${440*row.rate/100}" height="16" rx="4" fill="${index===strongestIndex ? orange : slate}"${index===strongestIndex ? ` stroke="${slate}" stroke-width="2"` : ''}/><text x="1128" y="${y}" text-anchor="end" fill="${ink}" font-size="${type.value}" font-weight="600">${row.rate.toFixed(1)}%</text>`;}).join('')}
      <text x="72" y="684" fill="${quiet}" font-size="${type.caption}">Share of ${num(report.summary.messages)} filtered messages · categories overlap</text>
      <text x="72" y="720" fill="${quiet}" font-size="${type.caption}">A working lens, not a fixed identity.</text><line x1="72" x2="1128" y1="750" y2="750" stroke="${slate}" stroke-opacity=".22" stroke-width="1"/>
      <text class="display" x="72" y="798" fill="${ink}" font-size="${type.section}">You have a rhythm.</text><text x="1128" y="798" text-anchor="end" fill="${quiet}" font-size="${type.caption}">${esc(report.timezone)}</text>
      ${report.rhythm.heatmap.map((row,day)=>`<text x="72" y="${840+day*32}" fill="${quiet}" font-size="${type.caption}">${days[day].slice(0,3)}</text>${row.map((value,h)=>{const size=rhythmMax ? Math.sqrt(value/rhythmMax)*26 : 0; return size ? `<rect x="${216+h*38+(26-size)/2}" y="${814+day*32+(26-size)/2}" width="${size}" height="${size}" fill="${value===rhythmMax ? orange : slate}"${value===rhythmMax ? ` stroke="${slate}" stroke-width="2"` : ''}/>` : '';}).join('')}`).join('')}
      ${[0,4,8,12,16,20,23].map(h=>`<text x="${229+h*38}" y="1068" text-anchor="middle" fill="${quiet}" font-size="${type.caption}">${String(h).padStart(2,'0')}</text>`).join('')}
      <text x="72" y="1108" fill="${quiet}" font-size="${type.caption}">Square area = messages · orange = peak</text>
      <text x="72" y="1150" fill="${quiet}" font-size="${type.caption}">${esc(coverage)}</text></svg>`;
  }

  async function saveCard(button) {
    button.disabled=true;
    try {
      await document.fonts.ready;
      const svg=cardSVG();
      const url=URL.createObjectURL(new Blob([svg],{type:'image/svg+xml'}));
      try {
        const image=new Image();
        await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=reject;image.src=url;});
        const canvas=document.createElement('canvas');canvas.width=1200;canvas.height=1200;
        canvas.getContext('2d').drawImage(image,0,0);
        const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));
        if (!blob) throw new Error('No image');
        download(blob,'my-opencode-mirror.png');
        status('Your share card is ready.');
      } finally {URL.revokeObjectURL(url);}
    } catch { status('The share card could not render. Try the HTML export.'); }
    finally {button.disabled=false;}
  }

  async function start() {
    const zone = settings.timezoneAuto && !report?.shared && location.protocol !== 'file:' ? localZone() : null;
    if (report && zone && zone !== report.timezone) {
      try {
        const response = await fetch('/api/timezone', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({timezone:zone})});
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Your local timezone could not be applied.');
        report = data;
        document.getElementById('report-data').textContent = JSON.stringify(report);
      } catch (error) { status(`${error.message} Showing ${report.timezone}.`); }
    }
    renderCurrent();
  }
  function renderCurrent() {
    if(!report) renderWelcome();
    else renderReport();
  }
  app.addEventListener('click',event=>{
    const button=event.target.closest('[data-action]');
    if(!button)return;
    if(button.dataset.action==='card')saveCard(button);
    if(button.dataset.action==='export')exportHTML();
    if(button.dataset.action==='archive')document.getElementById('archive-dialog').showModal();
  });
  start();
})();
