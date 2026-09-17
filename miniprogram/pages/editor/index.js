const { saveRecipe, getRecipe } = require('../../data/library');

Page({
  data: {
    name: '', summary: '', servings: '', time: '', note: '',
    categories: ['家常菜', '凉菜', '主食', '早餐', '海鲜', '汤羹', '地方特色菜'], category: '家常菜', categoryIndex: 0,
    ingredients: [{ name: '', amount: '' }], steps: [''],
    saving: false, saved: false, error: '', sourceType: 'manual', sourceUrl: '', canonicalUrl: '', sourceAuthor: '', warnings: [], loadingDraft: false, editing: false, loadFailed: false
  },
  async onLoad(options) {
    this.setData({ cloudEnabled: require('../../data/cloud').enabled() });
    this.recipeId = 'local-' + Date.now() + '-' + Math.random().toString(36).slice(2, 10);
    if (options.id) {
      this.recipeId = options.id;
      this.setData({ editing: true, loadingDraft: true });
      wx.setNavigationBarTitle({ title: '编辑菜谱' });
      try {
        const recipe = await getRecipe(options.id);
        if (!recipe) throw new Error('没有找到原菜谱，请返回后重新选择。');
        const categoryIndex = Math.max(0, this.data.categories.indexOf(recipe.category));
        this.setData({ cloudVersion: recipe.cloudVersion || 0, symbol: recipe.symbol, name: recipe.name, summary: recipe.summary || '', servings: recipe.servings === '份量未注明' ? '' : recipe.servings || '', time: recipe.time === '耗时未注明' ? '' : recipe.time || '', note: recipe.note || '', categoryIndex, category: this.data.categories[categoryIndex], ingredients: recipe.ingredients.map((item) => ({ name: item.name, amount: item.amount === '未注明' ? '' : item.amount })), steps: recipe.steps.slice(), sourceType: recipe.sourceType || 'seed', sourceUrl: recipe.sourceUrl || '', canonicalUrl: recipe.canonicalUrl || '', sourceAuthor: recipe.sourceAuthor || '', sourceTitle: recipe.sourceTitle || '' });
      } catch (error) {
        this.setData({ loadFailed: true, error: error.message || '读取失败，请返回重试。' });
      }
      this.setData({ loadingDraft: false });
      return;
    }
    if (options.imported) {
      this.setData({ loadingDraft: true });
      this.getOpenerEventChannel().on('importDraft', ({ draft, warnings }) => {
        const categoryIndex = Math.max(0, this.data.categories.indexOf(draft.category));
        this.setData({ name: draft.name, ingredients: draft.ingredients, steps: draft.steps, summary: draft.summary || '', servings: draft.servings || '', time: draft.time || '', note: draft.note || '', categoryIndex, category: this.data.categories[categoryIndex], sourceType: ['ai-text', 'ai-search'].includes(draft.sourceType) ? draft.sourceType : 'web', sourceTitle: draft.sourceTitle || '', sourceUrl: draft.sourceUrl || '', canonicalUrl: draft.canonicalUrl || '', sourceAuthor: draft.sourceAuthor || '', warnings: warnings || [], loadingDraft: false });
        wx.setNavigationBarTitle({ title: '确认导入菜谱' });
        this.markDirty();
      });
    }
  },
  markDirty() {
    if (!this.dirty) {
      this.dirty = true;
      wx.enableAlertBeforeUnload({ message: '菜谱尚未保存，确定离开吗？' });
    }
  },
  onField(event) {
    this.markDirty();
    this.setData({ [event.currentTarget.dataset.field]: event.detail.value, error: '' });
  },
  onCategory(event) {
    this.markDirty();
    const categoryIndex = Number(event.detail.value);
    this.setData({ categoryIndex, category: this.data.categories[categoryIndex] });
  },
  onIngredient(event) {
    this.markDirty();
    const { index, field } = event.currentTarget.dataset;
    this.setData({ ['ingredients[' + index + '].' + field]: event.detail.value, error: '' });
  },
  addIngredient() {
    this.markDirty();
    this.setData({ ingredients: this.data.ingredients.concat({ name: '', amount: '' }) });
  },
  removeIngredient(event) {
    this.markDirty();
    const ingredients = this.data.ingredients.filter((_, i) => i !== Number(event.currentTarget.dataset.index));
    this.setData({ ingredients: ingredients.length ? ingredients : [{ name: '', amount: '' }] });
  },
  onStep(event) {
    this.markDirty();
    this.setData({ ['steps[' + event.currentTarget.dataset.index + ']']: event.detail.value, error: '' });
  },
  addStep() {
    this.markDirty();
    this.setData({ steps: this.data.steps.concat('') });
  },
  removeStep(event) {
    this.markDirty();
    const steps = this.data.steps.filter((_, i) => i !== Number(event.currentTarget.dataset.index));
    this.setData({ steps: steps.length ? steps : [''] });
  },
  async onSave() {
    if (this.data.saving || this.data.saved || this.data.loadingDraft || this.data.loadFailed) return;
    this.setData({ saving: true, error: '' });
    try {
      await saveRecipe(this.data, this.recipeId, this.data.editing);
    } catch (error) {
      this.setData({ saving: false, error: error.message || '保存失败，填写内容已保留，请重试。' });
      return;
    }
    this.setData({ saving: false, saved: true });
    wx.disableAlertBeforeUnload();
    wx.showToast({ title: this.data.cloudEnabled ? '已保存到共享菜谱' : '已保存到本机', icon: 'success' });
    const pages = getCurrentPages();
    const previous = pages[pages.length - 2];
    if (previous && typeof previous.onReset === 'function') previous.onReset();
    this.onViewSaved();
  },
  onViewSaved() {
    const pages = getCurrentPages();
    const previous = pages[pages.length - 2];
    if (this.data.editing && previous && previous.route === 'pages/detail/index') {
      wx.navigateBack({ delta: 1, fail: () => this.setData({ error: '已保存，返回失败，请点击查看菜谱重试。' }) });
      return;
    }
    wx.redirectTo({
      url: '/pages/detail/index?id=' + encodeURIComponent(this.recipeId),
      fail: () => this.setData({ error: '菜谱已保存，可点击下方按钮再次打开，或返回列表查看。' })
    });
  }
});
