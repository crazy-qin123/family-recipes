const cloud = require('../../data/cloud');
const { readCustom } = require('../../data/library');

Page({
  data: { enabled: false, token: '', busy: false, error: '', message: '' },
  onShow() { this.setData({ enabled: cloud.enabled() }); },
  onInput(event) { this.setData({ token: event.detail.value }); },
  async onConnect() {
    if (this.data.busy) return;
    this.setData({ busy: true, error: '', message: '' });
    const previous = wx.getStorageSync('family-recipes.connection.v1');
    try {
      cloud.configure(this.data.token.trim());
      await cloud.call('/api/shared/list', { collection: 'recipes', offset: 0 });
      this.setData({ enabled: true, token: '', message: '已连接家庭共享。原有本机数据仍然保留。' });
    } catch (error) {
      if (previous) wx.setStorageSync('family-recipes.connection.v1', previous);
      else cloud.disable();
      this.setData({ error: error.message });
    } finally { this.setData({ busy: false }); }
  },
  onDisconnect() {
    if (this.data.busy) return;
    cloud.disable();
    this.setData({ enabled: false, token: '', message: '已切回本机数据，云端内容保持不变。' });
  },
  onClearLocal() {
    wx.showModal({ title: '清空本机菜谱和清单？', content: '这只清理当前设备，不影响云端。操作不可恢复。', confirmText: '清空', confirmColor: '#983e2d', success: (r) => {
      if (!r.confirm) return;
      require('../../data/library').clearLocal();
      require('../../data/shopping').clearLocal();
      this.setData({ message: '本机菜谱和买菜清单已清空。' });
    } });
  },
  onMigrate() {
    if (this.data.busy || !cloud.enabled()) return;
    wx.showModal({ title: '复制本机菜谱到家庭共享？', content: '保留本机原件。云端已有相同编号的菜谱不会被覆盖。买菜清单单独复制。', success: (r) => { if (r.confirm) this.migrate(); } });
  },
  async migrate() {
    this.setData({ busy: true, error: '', message: '' });
    let saved = 0, skipped = 0;
    try {
      for (const recipe of readCustom()) {
        try {
          await cloud.call('/api/shared/save', { collection: 'recipes', version: 0, item: { id: recipe.id, data: recipe } });
          saved++;
        } catch (error) { if (error.status === 409) skipped++; else throw error; }
      }
      this.setData({ message: '已复制 ' + saved + ' 道，已有同编号内容跳过 ' + skipped + ' 道。本机原件已保留。' });
    } catch (error) { this.setData({ error: '已完成 ' + saved + ' 道。' + error.message + '，可再次点击继续复制。' }); }
    finally { this.setData({ busy: false }); }
  },
  onMigrateShopping() {
    if (this.data.busy || !cloud.enabled()) return;
    wx.showModal({ title: '复制本机买菜清单？', content: '保留原件与购买状态。相同编号不会重复添加。', success: async (r) => {
      if (!r.confirm) return;
      this.setData({ busy: true, error: '', message: '' });
      try {
        const count = await require('../../data/shopping').migrateLocal();
        this.setData({ message: '已复制 ' + count + ' 项，本机原件已保留。' });
      } catch (error) { this.setData({ error: error.message }); }
      finally { this.setData({ busy: false }); }
    } });
  }
});
