// 开发服务器代理到 Flask 后端
// 保持与后端蓝图前缀一致（/api）
module.exports = {
  devServer: {
    client: {
      // 仅显示错误，不显示警告；如需彻底关闭 overlay，可设置环境变量 VUE_APP_OVERLAY=false
      overlay: process.env.VUE_APP_OVERLAY === 'false' ? false : { errors: true, warnings: false }
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
        // Flask 蓝图已使用 /api 前缀，此处保留路径
        pathRewrite: { '^/api': '/api' },
      },
    },
  },
};
