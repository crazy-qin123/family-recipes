const { categories } = require('../../data/recipes');
const { listRecipes } = require('../../data/library');
const library = require('../../data/library');

Page({
  data: {
    keyword: '', category: '全部', categories,
    recipes: [], error: '', openId: ''
  },
  onShow() { this.refresh(); },
  async refresh() {
    const requestId = this.requestId = (this.requestId || 0) + 1;
    this.setData({ cloudEnabled: require('../../data/cloud').enabled() });
    try {
      const recipes = await listRecipes(this.data.keyword, this.data.category);
      if (requestId !== this.requestId) return;
      this.setData({ recipes, error: '' });
    } catch (error) {
      if (requestId !== this.requestId) return;
      this.setData({ recipes: [], error: error.message || '菜谱读取失败，请重试。' });
    }
  },
  onSearch(event) {
    const keyword = event.detail.value;
    this.setData({ keyword });
    this.refresh();
  },
  onCategory(event) {
    const category = event.currentTarget.dataset.category;
    this.setData({ category });
    this.refresh();
  },
  onReset() {
    this.setData({ keyword: '', category: '全部' });
    this.refresh();
  },
  onOpen(event) {
    if (this.data.openId) { this.setData({ openId: '' }); return; }
    wx.navigateTo({ url: '/pages/detail/index?id=' + encodeURIComponent(event.currentTarget.dataset.id) });
  },
  onTouchStart(event) { this.touchX = event.touches[0].clientX; },
  onTouchEnd(event) { const dx = event.changedTouches[0].clientX - this.touchX; const id = event.currentTarget.dataset.id; if (dx < -50) this.setData({ openId: id }); else if (dx > 50) this.setData({ openId: '' }); },
  onDelete(event) { const recipe = this.data.recipes.find((item) => item.id === event.currentTarget.dataset.id); if (!recipe) return; wx.showModal({ title: '删除菜谱？', content: '删除后家庭成员也将看不到这道菜。', success: async (r) => { if (!r.confirm) return; try { await library.removeRecipe(recipe); this.setData({ openId: '' }); this.refresh(); } catch (e) { wx.showToast({ title: e.message || '删除失败', icon: 'none' }); } } }); },
  onAdd() {
    wx.showActionSheet({
      itemList: ['手动填写', '粘贴菜谱 · AI 整理', '搜索菜名'],
      success: ({ tapIndex }) => {
        if (tapIndex === 0) {
          wx.navigateTo({ url: '/pages/editor/index' });
        } else if (tapIndex === 1) {
          wx.navigateTo({ url: '/pages/paste/index' });
        } else {
          wx.navigateTo({ url: '/pages/search/index' });
        }
      }
    });
  },
  onSettings() { wx.navigateTo({ url: '/pages/settings/index' }); },
  onShopping() {
    wx.navigateTo({ url: '/pages/shopping/index' });
  }
});
