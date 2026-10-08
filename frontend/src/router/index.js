import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import LegalView from '../views/LegalView.vue'
import AdminView from '../views/AdminView.vue'
import LoginView from '../views/LoginView.vue'
import PayReturnView from '../views/PayReturnView.vue'
import CabinetView from '../views/CabinetView.vue'
import PricesView from '../views/PricesView.vue'
import SupportView from '../views/SupportView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/login', name: 'login', component: LoginView },
    { path: '/cabinet', name: 'cabinet', component: CabinetView },
    { path: '/cabinet/support', name: 'cabinet-support', component: SupportView },
    { path: '/support', name: 'support', component: SupportView },
    { path: '/prices', name: 'prices', component: PricesView },
    { path: '/pay/return/:topup/:token', name: 'pay-return', component: PayReturnView },
    { path: '/pay/return', name: 'pay-return-query', component: PayReturnView },
    { path: '/privacy', name: 'privacy', component: LegalView, props: { page: 'privacy' } },
    { path: '/consent', name: 'consent', component: LegalView, props: { page: 'consent' } },
    { path: '/offer', name: 'offer', component: LegalView, props: { page: 'offer' } },
    { path: '/admin', redirect: '/admin-panel' },
    { path: '/admin-panel', name: 'admin', component: AdminView },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router
