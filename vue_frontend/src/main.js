// 应用入口：挂载 Vue 应用、注册 Element Plus、挂载路由
import { createApp } from 'vue';
import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';
import '@/assets/styles/auth-common.css';
import App from './App.vue';
import router from './router';

const app = createApp(App);
app.use(ElementPlus);
app.use(router);
app.mount('#app');
