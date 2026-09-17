const { getRecipe } = require('../../data/library');
const { addItems } = require('../../data/shopping');

Page({
  data: { recipe: null, error: '', ingredientOptions: [], selected: [], adding: false, added: false, shoppingError: '' },
  onLoad(options) {
    try { this.recipeId = decodeURIComponent(options.id || ''); } catch (error) { this.recipeId = options.id || ''; }
  },
  async onShow() {
    this.setData({ cloudEnabled: require('../../data/cloud').enabled() });
    try {
      const recipe = await getRecipe(this.recipeId);
      if (!recipe) throw new Error('没有找到这道云端菜谱，请返回首页刷新后再试。');
      this.setData({ recipe, selected: [], added: false, error: '', shoppingError: '', ingredientOptions: recipe ? recipe.ingredients.map((item, index) => Object.assign({}, item, { value: String(index), checked: false })) : [] });
      if (recipe) wx.setNavigationBarTitle({ title: recipe.name });
    } catch (error) {
      this.setData({ recipe: null, error: error.message || '读取失败，请返回重试。' });
    }
  },
  onSelectIngredients(event) {
    const selected = event.detail.value;
    this.setData({ selected, ingredientOptions: this.data.ingredientOptions.map((item) => Object.assign({}, item, { checked: selected.includes(item.value) })), shoppingError: '', added: false });
  },
  async onAddShopping() {
    if (this.data.adding || !this.data.selected.length) return;
    this.setData({ adding: true, shoppingError: '' });
    try {
      const ingredients = this.data.selected.map((index) => this.data.recipe.ingredients[Number(index)]);
      await addItems(ingredients, this.data.recipe.name);
      this.setData({ selected: [], ingredientOptions: this.data.ingredientOptions.map((item) => Object.assign({}, item, { checked: false })), added: true });
      wx.showToast({ title: '已加入清单', icon: 'success' });
    } catch (error) {
      this.setData({ shoppingError: error.message || '加入失败，请重试。' });
    }
    this.setData({ adding: false });
  },
  onShopping() {
    wx.navigateTo({ url: '/pages/shopping/index' });
  },
  onEdit() {
    if (this.data.recipe) wx.navigateTo({ url: '/pages/editor/index?id=' + encodeURIComponent(this.recipeId) });
  },
  onHome() {
    wx.reLaunch({ url: '/pages/recipes/index' });
  }
});
