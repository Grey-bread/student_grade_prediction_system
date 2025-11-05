// 开发服务器代理到 Flask 后端
// 保持与后端蓝图前缀一致（/api）
module.exports = {
  devServer: {
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
