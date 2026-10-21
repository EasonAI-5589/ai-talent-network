(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.TalentCatalog = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const TITLE_LABELS = {assistant:'助理教授',associate:'副教授',professor:'教授',honorary:'荣誉 / 名誉 / 退休教职',other:'其他已记载职称',unknown:'职称未知'};
  const THEME_LABELS = {asset_pricing:'资产定价',corporate_finance:'公司金融',macro:'宏观经济 / 宏观金融',labour:'劳动经济',development:'发展经济',econometrics:'计量 / 统计',banking:'银行 / 金融中介',household:'家庭金融',trade:'国际贸易',behavioural:'行为经济 / 金融',market_design:'市场设计 / 博弈论'};
  const METHOD_LABELS = {ai_method:'AI / 机器学习方法',ai_impact:'AI 的经济与社会影响',ai_unspecified:'其他 AI 线索（方法待核）',fintech:'金融科技',causal:'因果推断',structural:'结构估计'};
  const themeRules = [
    ['asset_pricing', /asset pric|derivative pric|资产定价|衍生品定价/i], ['corporate_finance', /corporate financ|corporate govern|公司金融|公司治理/i],
    ['macro', /macroeconom|macro.financ|宏观/i], ['labour', /labo[u]?r|employment|wage|劳动|就业|工资/i],
    ['development', /development econom|economic development|发展经济|经济发展/i], ['econometrics', /econometric|statistic|计量|统计/i],
    ['banking', /banking|financial intermedi|银行|金融中介/i], ['household', /household financ|家庭金融/i],
    ['trade', /international trade|国际贸易/i], ['behavioural', /behavio[u]?ral|行为/i], ['market_design', /market design|game theor|市场设计|博弈/i]
  ];
  const sourceKind = p => p.source_kind || (p.reference ? 'hong_kong' : 'bibliographic');
  const recordKey = p => p._record_id || p.id + '@' + p.school;
  const roleState = p => p.current_role ? (p.current_role.evidence_status === 'official_verified' ? 'ok' : p.current_role.evidence_status === 'conflicting' ? 'bad' : 'none') : p.verify && !/未单独检索/.test(p.verify.title || '') && p.verify.url ? 'legacy' : 'none';
  const institutionKnown = p => Boolean(p.display_role?.institution || p.current_role?.institution && (roleState(p) === 'ok' || p.current_role.institution_evidence_status === 'official_verified'));
  // "bad" means official pages were read but do not give one current appointment; that is a definite finding, not a gap.
  // A search can fail because of access, identity, or missing evidence; it does not prove there is no official page.
  const NOT_FOUND = '现职未能核实';
  const searched = p => !p.current_role && p.role_search?.status === 'no_verifiable_official_page';
  function searchOutcome(p) {
    if (!searched(p)) return null;
    const r = p.role_search;
    const reasons = {not_found:'未检索到官方任职页面',fetch_blocked:'官方页面读取受阻',identity_unresolved:'身份或现职无法确认',historical_only:'仅找到历史任职证据',outside_scope:'仅找到高校范围外任职材料',quote_unmatched:'页面内容未通过核对'};
    return {checkedAt:r.checked_at || '',reason:reasons[r.reason_code] || '现职证据未能核实',note:r.note || '',urls:[...new Set((r.attempted_urls || []).filter(u=>safeUrl(u)))]};
  }
  const institution = p => p.display_role?.institution || (institutionKnown(p) ? p.current_role.institution : roleState(p) === 'bad' ? '官方页面机构不唯一' : searched(p) ? NOT_FOUND : '待核实');
  const appointments = p => {
    const role = p.display_role || p.current_role;
    return institutionKnown(p) && Array.isArray(role?.appointments) ? role.appointments.filter(a => ['current','emeritus'].includes(a.status)) : [];
  };
  const institutions = p => {
    if (p.display_role?.institution) return [p.display_role.institution];
    const names = appointments(p).map(a => a.institution).filter(Boolean);
    return names.length ? [...new Set(names)] : [institution(p)];
  };
  const position = p => p.display_role?.position || (roleState(p) === 'ok' ? p.current_role.position || '待核实' : roleState(p) === 'bad' ? '官方页面职称不唯一' : searched(p) ? NOT_FOUND : '待核实');
  const department = p => institutionKnown(p) ? (p.display_role || p.current_role).department || '待核实' : '待核实';
  // A verified appointment always wins over the reference sheet's own wording, which stays available as "sheet".
  const verifiedText = (p, field) => roleState(p) === 'ok' && (p.display_role || p.current_role)[field] ? String((p.display_role || p.current_role)[field]) : '';
  const effectivePosition = p => p.display_role ? p.display_role.position || '' : roleState(p) === 'ok' ? verifiedText(p, 'position') : roleState(p) === 'bad' ? '' : (p.reference?.academic_title_raw || p.current_role?.position || '');
  const effectiveDepartment = p => p.display_role ? p.display_role.department || '' : roleState(p) === 'ok' ? verifiedText(p, 'department') : (p.reference?.department_raw || (institutionKnown(p) ? p.current_role?.department : '') || '');
  const departmentLabel = p => effectiveDepartment(p) || '未知';
  function detailProfile(p) {
    const r = p.reference || {}, role = p.display_role || p.current_role || {};
    const value = v => v == null || v === '' ? '未记载' : String(v);
    const list = v => Array.isArray(v) ? v.filter(Boolean).map(String) : [];
    const w = p.profile;
    if (w) {
      // The delivery workbook row is the reviewed record for this person; show it as one bilingual profile.
      const pair = (zh, en) => zh && en ? `${zh} / ${en}` : (zh || en || '');
      return {
        research: value(w.research),
        discipline: value(pair(w.discipline_zh, w.discipline_en)),
        institution: value(pair(w.institution_zh, w.institution_en)),
        title: value(pair(w.title_zh, w.title_en)),
        department: value(pair(w.department_zh, w.department_en)),
        adminRole: pair(w.admin_zh, w.admin_en),
        phdInstitution: value(pair(w.phd_zh, w.phd_en)),
        phdYear: value(w.phd_year),
        firstAssistantProfessor: value(w.first_ap_year),
        associateProfessorPromotion: value(w.associate_year),
        tenure: value(w.tenure_year),
        professorPromotion: value(w.full_year),
        email: value(w.email),
        profileUrls: list(w.profile_urls),
        departmentUrls: w.school_url ? [String(w.school_url)] : [],
        sheet: null
      };
    }
    const profileUrls = p.display_role?.source_url ? [p.display_role.source_url] : list(r.profile_urls);
    if (!profileUrls.length) profileUrls.push(...list(p.profile_urls));
    if (!profileUrls.length && role.source_url) profileUrls.push(String(role.source_url));
    const same = (a, b) => String(a ?? '').replace(/\s+/g, ' ').trim().toLowerCase() === String(b ?? '').replace(/\s+/g, ' ').trim().toLowerCase();
    let sheet = null;
    if (p.reference && roleState(p) === 'ok') {
      const raw = {institution: r.institution_raw || '', title: r.academic_title_raw || '', department: r.department_raw || ''};
      const differs = (text, ...verified) => Boolean(text) && !verified.some(v => same(v, text));
      sheet = {
        ...raw,
        titleDiffers: differs(raw.title, role.position),
        anyDiffers: differs(raw.institution, role.institution, role.institution_en) || differs(raw.title, role.position) || differs(raw.department, role.department)
      };
    }
    return {
      research: value(r.research_interests_raw || (p.topics || []).join(' · ')),
      discipline: value(r.discipline_raw || p.home),
      institution: value(p.display_role?.institution || verifiedText(p, 'institution') || r.institution_raw || role.institution || p.school_zh || p.school),
      title: value(p.display_role?.position || (roleState(p) === 'bad' ? '官方页面职称不唯一' : roleState(p) === 'ok' ? effectivePosition(p)
        : r.academic_title_raw ? `${r.academic_title_raw}（表内记载）` : searched(p) ? NOT_FOUND : effectivePosition(p))),
      department: value(effectiveDepartment(p)),
      phdInstitution: value(r.phd_institution_raw),
      phdYear: value(r.phd_year),
      firstAssistantProfessor: value(r.first_assistant_professor_raw),
      associateProfessorPromotion: value(r.associate_professor_promotion_raw),
      tenure: value(r.tenure_raw),
      professorPromotion: value(r.professor_promotion_year),
      email: value(r.email_raw),
      profileUrls,
      departmentUrls: list(r.department_urls),
      sheet
    };
  }
  function titleCategories(p) {
    const texts = p.display_role || roleState(p) === 'ok' ? appointments(p).map(a => a.position).filter(Boolean) : [];
    if (!texts.length) texts.push(p.display_role ? p.display_role.position || '' : verifiedText(p, 'position') || p.reference?.academic_title_raw || '');
    return [...new Set(texts.map(text => {
      if (!text) return 'unknown';
      if (/honorary|emerit|retired|荣誉|名誉|退休/i.test(text)) return 'honorary';
      if (/assistant professor|助理教授/i.test(text)) return 'assistant';
      if (/associate professor|副教授/i.test(text)) return 'associate';
      if (/professor|教授/i.test(text)) return 'professor';
      return 'other';
    }))];
  }
  const researchCache = new WeakMap();
  function deriveResearch(p) {
    if (researchCache.has(p)) return researchCache.get(p);
    const texts = [
      ...(p.profile?.research ? [{text:String(p.profile.research),source:'官网研究领域'}] : []),
      ...(p.reference?.research_interests_raw && !p.profile?.research ? [{text:String(p.reference.research_interests_raw),source:'参考表研究领域'}] : []),
      ...(p.topics || []).map(text=>({text,source:'已有研究主题'})),
      ...(p.papers || []).map(w=>({text:w.title,source:'论文标题'}))
    ].filter(x=>x.text);
    const themes = new Set(), methods = new Set(), evidence = [];
    const add = (kind,key,item) => { (kind === 'theme' ? themes : methods).add(key); evidence.push({kind,key,text:item.text,source:item.source}); };
    for (const item of texts) {
      for (const [key,pattern] of themeRules) if(pattern.test(item.text)) add('theme',key,item);
      const impact = /(?:artificial intelligence|\bAI\b|automation|robots?|人工智能|自动化|机器人)/i.test(item.text) && /labo[u]?r|employment|jobs|wage|economic impact|economics of|social impact|future of work|劳动|就业|经济影响|社会影响|经济学/i.test(item.text);
      const method = /machine learning|deep learning|neural network|reinforcement learning|large language model|机器学习|深度学习|神经网络|强化学习|大语言模型/i.test(item.text);
      if(method) add('method','ai_method',item);
      if(impact) add('method','ai_impact',item);
      if(!method && !impact && /artificial intelligence|\bAI\b|人工智能/i.test(item.text)) add('method','ai_unspecified',item);
      if(/fin\s*tech|finance and technology|financial technolog|blockchain|cryptocurrenc|decentralized financ|金融科技|区块链|加密货币/i.test(item.text)) add('method','fintech',item);
      if(/causal infer|causal effect|因果推断|因果效应/i.test(item.text)) add('method','causal',item);
      if(/structural estim|structural econom|结构估计/i.test(item.text)) add('method','structural',item);
    }
    const result = {themes:[...themes],methods:[...methods],evidence}; researchCache.set(p,result); return result;
  }
  function filterPeople(people, state = {}) {
    const any = (selected, values) => !selected?.length || selected.some(x=>values.includes(x));
    const active = value => value != null && value !== '' && value !== '全部' && value !== 'all';
    const q = String(state.q || '').toLowerCase().trim();
    return people.filter(p => {
      const r = deriveResearch(p), ref = p.reference || {};
      if(active(state.source) && sourceKind(p) !== state.source) return false;
      if(active(state.region) && p.region !== state.region) return false;
      if(active(state.school) && p.school !== state.school) return false;
      if(active(state.currentSchool) && !institutions(p).includes(state.currentSchool)) return false;
      if(state.tier === 'unknown' ? p.tier != null : state.tier && p.tier !== state.tier) return false;
      if(state.home && p.home !== state.home) return false;
      if(state.hideEarly && p.early) return false;
      if(active(state.vf) && roleState(p) !== state.vf) return false;
      if(!any(state.titles,titleCategories(p)) || !any(state.themes,r.themes) || !any(state.methods,r.methods)) return false;
      if(active(state.department) && departmentLabel(p) !== state.department) return false;
      const year = p.profile?.phd_year ?? ref.phd_year;
      const known = year != null && year !== '' && Number.isInteger(Number(year));
      if(state.yearStatus === 'unknown' && known || state.yearStatus === 'known' && !known) return false;
      if(active(state.phdFrom) || active(state.phdTo)) {
        if(!known || active(state.phdFrom) && Number(year) < Number(state.phdFrom) || active(state.phdTo) && Number(year) > Number(state.phdTo)) return false;
      }
      const w = p.profile || {};
      if(q && ![p.name,p.name_zh,p.school,p.school_zh,p.unit,institution(p),position(p),(p.display_role || p.current_role)?.institution_en,effectiveDepartment(p),p.home,ref.academic_title_raw,ref.department_raw,ref.discipline_raw,ref.research_interests_raw,ref.phd_institution_raw,w.name_en,w.title_en,w.department_en,w.discipline_zh,w.discipline_en,w.research,w.phd_zh,w.phd_en,w.admin_zh,w.admin_en,...(p.topics || []),...(p.papers || []).map(x=>x.title)].join(' ').toLowerCase().includes(q)) return false;
      return true;
    });
  }
  const numeric = n => n !== null && n !== undefined && n !== '' && Number.isFinite(Number(n));
  const titleRank = p => {
    const text = p.display_role ? p.display_role.position || '' : verifiedText(p, 'position') || p.reference?.academic_title_raw || (p.current_role?.position || '');
    if (/professor|教授/i.test(text) && !/associate|assistant|副教授|助理教授/i.test(text)) return 3;
    if (/associate|副教授/i.test(text)) return 2;
    if (/assistant|助理教授/i.test(text)) return 1;
    if (text) return 0;
    return -1;
  };
  function sortPeople(people, field = 'fit') {
    if (field === 'title' || field === 'position') {
      return [...people].sort((a,b) => titleRank(b) - titleRank(a) || (numeric(b.fit) ? Number(b.fit) : -Infinity) - (numeric(a.fit) ? Number(a.fit) : -Infinity) || (numeric(b.score) ? Number(b.score) : -Infinity) - (numeric(a.score) ? Number(a.score) : -Infinity));
    }
    const k = field === 'ai' ? 'ai_papers' : field;
    const desc = (a,b,f) => numeric(a[f]) && numeric(b[f]) ? Number(b[f])-Number(a[f]) : numeric(a[f]) ? -1 : numeric(b[f]) ? 1 : 0;
    return [...people].sort((a,b)=>desc(a,b,k) || desc(a,b,'score'));
  }
  const formatNumber = n => numeric(n) ? Number(n).toLocaleString('en-US') : '—';
  function safeUrl(value) {
    if(typeof value !== 'string' || /[\u0000-\u001f\u007f]/.test(value)) return '';
    const text = value.trim();
    if(!/^(https?:\/\/|mailto:)/i.test(text)) return '';
    try { const url = new URL(text); return ['http:','https:','mailto:'].includes(url.protocol) && (url.protocol==='mailto:' ? Boolean(url.pathname) : Boolean(url.hostname)) ? text : ''; } catch { return ''; }
  }
  const openAlexUrl = p => sourceKind(p) !== 'hong_kong' && /^A\d+$/.test(p.id || '') ? 'https://openalex.org/' + p.id : '';
  function toTSV(rows) {
    return rows.map(row=>row.map(value=>{let text = String(value ?? '').replace(/[\t\r\n]+/g,' '); if(/^\s*[=+\-@]/.test(text)) text="'"+text; return text;}).join('\t')).join('\n');
  }
  async function request(path, method, body, options={}) {
    const response=await fetch((options.base || '')+path,{method,headers:{'Content-Type':'application/json','X-Talent-Request':'1'},body:JSON.stringify(body)});
    let payload; try {payload=await response.json();} catch {throw new Error('服务返回了无法读取的响应');}
    if(!response.ok) throw new Error(payload.error || `保存失败（HTTP ${response.status}）`);
    return payload;
  }
  async function saveShortlist(id, selected, options) {
    const result=await request('/api/shortlist/'+encodeURIComponent(id),'PUT',{selected},options);
    if(result.record_id !== id || result.selected !== selected) throw new Error('保存结果与请求不一致，请刷新核对');
    return result;
  }
  async function resetShortlist(options) {
    const result=await request('/api/shortlist/reset','POST',{},options);
    if(result.ok !== true) throw new Error('恢复默认未获得服务确认');
    return result;
  }
  return {TITLE_LABELS,THEME_LABELS,METHOD_LABELS,NOT_FOUND,searched,searchOutcome,sourceKind,recordKey,roleState,institutionKnown,institution,institutions,department,position,effectivePosition,effectiveDepartment,departmentLabel,detailProfile,titleCategories,deriveResearch,filterPeople,sortPeople,titleRank,formatNumber,safeUrl,openAlexUrl,toTSV,saveShortlist,resetShortlist};
});
