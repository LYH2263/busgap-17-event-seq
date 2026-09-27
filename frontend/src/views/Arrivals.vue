<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
const rows = ref<any[]>([])
const route = useRoute()
const tripNo = computed(() => (route.query.trip_no as string) || '')
const filtered = computed(() => tripNo.value ? rows.value.filter(r => r.trip_no === tripNo.value) : rows.value)
onMounted(async () => { rows.value = await api('/arrivals') })
</script>
<template>
  <h1>到站</h1>
  <p class="sub">各班次实际到站记录</p>
  <p v-if="tripNo" class="sub">筛选班次 {{ tripNo }} · <RouterLink to="/arrivals" class="bg-trip-link">清除筛选</RouterLink></p>
  <div class="card">
    <table>
      <thead><tr><th>班次</th><th>站序</th><th>站点</th><th>实际到站</th></tr></thead>
      <tbody>
        <tr v-for="r in filtered" :key="r.id ?? JSON.stringify(r)"><td>{{ r.trip_no }}</td><td>{{ r.stop_seq }}</td><td>{{ r.stop_name }}</td><td>{{ r.actual_arrive }}</td></tr>
      </tbody>
    </table>
  </div>
</template>
