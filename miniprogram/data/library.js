const seed = require('./recipes');
const KEY = 'family-recipes.custom.v1';
const cloud = require('./cloud');

async function sharedRecipes() {
  const symbols = { 家常菜: '🍳', 凉菜: '🥗', 主食: '🍚', 早餐: '🥣', 海鲜: '🦐', 汤羹: '🍲', 地方特色菜: '🥢' };
  return (await cloud.list('recipes')).map((r) => Object.assign({}, r.data, {
    id: r.id, symbol: r.data.symbol || symbols[r.data.category] || '🍽️',
    cloudVersion: r.version, createdAt: r.created_at, updatedAt: r.updated_at
  }));
}

function readCustom() {
  const value = wx.getStorageSync(KEY);
  if (value === '' || value === undefined || value === null) return [];
  if (!Array.isArray(value) || value.some((r) => !r || typeof r.id !== 'string' || typeof r.name !== 'string' || !Array.isArray(r.ingredients) || !Array.isArray(r.steps))) {
    throw new Error('本地菜谱数据无法读取，请勿清理缓存，先联系开发者检查。');
  }
  return value;
}

async function listRecipes(keyword, category) {
  const query = (keyword || '').trim().toLowerCase();
  const custom = cloud.enabled() ? await sharedRecipes() : readCustom();
  if (cloud.enabled() || wx.getStorageSync('family-recipes.hide-seeds.v1') === true) {
    return custom.filter((r) =>
      (!category || category === '全部' || r.category === category) &&
      [r.name].concat((r.ingredients || []).map((i) => i.name)).join(' ').toLowerCase().includes(query)
    );
  }
  const ids = new Set(custom.map((recipe) => recipe.id));
  return custom.concat(seed.recipes.filter((recipe) => !ids.has(recipe.id))).filter((r) =>
    (!category || category === '全部' || r.category === category) &&
    [r.name].concat(r.ingredients.map((i) => i.name)).join(' ').toLowerCase().includes(query)
  );
}

async function getRecipe(id) {
  let decoded = id;
  try { decoded = decodeURIComponent(id); } catch (error) { /* keep original id */ }
  if (cloud.enabled() || wx.getStorageSync('family-recipes.hide-seeds.v1') === true) return (await sharedRecipes()).find((r) => r.id === id || r.id === decoded);
  return readCustom().find((r) => r.id === id) || seed.getRecipe(id);
}

function prepareRecipe(form) {
  const name = form.name.trim();
  if (!name) throw new Error('请填写菜名。');
  const ingredients = form.ingredients.filter((i) => i.name.trim() || i.amount.trim()).map((i) => {
    if (!i.name.trim()) throw new Error('有一项食材只有用量，请补充食材名称。');
    return { name: i.name.trim(), amount: i.amount.trim() || '未注明' };
  });
  if (!ingredients.length) throw new Error('请至少填写一项食材。');
  const steps = form.steps.map((s) => s.trim()).filter(Boolean);
  if (!steps.length) throw new Error('请至少填写一个制作步骤。');
  return {
    name, ingredients, steps, category: form.category,
    summary: form.summary.trim() || '收录一份自家的味道。',
    servings: form.servings.trim() || '份量未注明',
    time: form.time.trim() || '耗时未注明', note: form.note.trim(),
    symbol: '🍽️', sourceType: ['web', 'ai-text', 'ai-search'].includes(form.sourceType) ? form.sourceType : 'manual', sourceTitle: form.sourceTitle || '',
    sourceUrl: form.sourceUrl || '', canonicalUrl: form.canonicalUrl || '', sourceAuthor: form.sourceAuthor || '', imageUrl: form.imageUrl || ''
  };
}

async function saveRecipe(form, id, editing = false) {
  const recipe = prepareRecipe(form);
  if (cloud.enabled()) {
    const version = editing ? form.cloudVersion || 0 : 0;
    if (editing) {
      recipe.sourceType = form.sourceType || 'seed';
      recipe.symbol = form.symbol || recipe.symbol;
    }
    const result = await cloud.call('/api/shared/save', { collection: 'recipes', item: { id, data: recipe }, version });
    return Object.assign({}, result.item.data, { cloudVersion: result.item.version });
  }
  const existing = readCustom();
  // 同一次保存沿用 ID，避免重试生成两条记录。
  const original = existing.find((r) => r.id === id) || seed.getRecipe(id);
  if (editing && !original) throw new Error('原菜谱不存在，请返回菜谱库重新选择。');
  const now = new Date().toISOString();
  const saved = Object.assign({}, recipe, { id, createdAt: original && original.createdAt || now, updatedAt: now });
  if (original) {
    saved.symbol = original.symbol || recipe.symbol;
    saved.sourceType = original.sourceType || 'seed';
    ['sourceUrl', 'canonicalUrl', 'sourceAuthor', 'sourceTitle'].forEach((key) => { saved[key] = original[key] || ''; });
  }
  wx.setStorageSync(KEY, [saved].concat(existing.filter((r) => r.id !== id)));
  return saved;
}

function clearLocal() { wx.removeStorageSync(KEY); wx.setStorageSync('family-recipes.hide-seeds.v1', true); }
async function removeRecipe(recipe) { if (cloud.enabled()) { await cloud.call('/api/shared/remove', { collection: 'recipes', id: recipe.id, version: recipe.cloudVersion }); return; } wx.setStorageSync(KEY, readCustom().filter((r) => r.id !== recipe.id)); }

module.exports = { listRecipes, getRecipe, prepareRecipe, saveRecipe, removeRecipe, readCustom, clearLocal };
