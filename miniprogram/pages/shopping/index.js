const { readItems, addItems, toggleItem, removeItem } = require('../../data/shopping');

Page({
  data: { pending: [], completed: [], name: '', amount: '', error: '', busy: false, loaded: false },
  onShow() { this.refresh(); },
  async refresh() {
    this.setData({ cloudEnabled: require('../../data/cloud').enabled() });
    try {
      const items = (await readItems()).map((item) => Object.assign({}, item, { sourceLabel: item.sources.join('、') }));
      this.setData({ pending: items.filter((item) => !item.done), completed: items.filter((item) => item.done), loaded: true, error: '' });
    } catch (error) {
      this.setData({ loaded: false, error: error.message || '读取失败，请重试。' });
    }
  },
  onField(event) {
    this.setData({ [event.currentTarget.dataset.field]: event.detail.value });
  },
  async mutate(action) {
    if (this.data.busy) return;
    this.setData({ busy: true, error: '' });
    let success = false;
    try { await action(); success = true; await this.refresh(); }
    catch (error) { this.setData({ error: error.message || '保存失败，请重试。' }); }
    this.setData({ busy: false });
    return success;
  },
  async onAdd() {
    if (await this.mutate(() => addItems([{ name: this.data.name, amount: this.data.amount }], '手动添加'))) {
      this.setData({ name: '', amount: '' });
      wx.showToast({ title: '已添加', icon: 'success' });
    }
  },
  onToggle(event) {
    this.mutate(() => toggleItem(event.currentTarget.dataset.id));
  },
  onDelete(event) {
    const { id, name } = event.currentTarget.dataset;
    wx.showModal({ title: '删除这项食材？', content: name, confirmText: '删除', confirmColor: '#983e2d', success: ({ confirm }) => {
      if (confirm) this.mutate(() => removeItem(id));
    } });
  }
});
