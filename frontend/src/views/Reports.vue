<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const trips = ref<any[]>([])
const events = ref<any[]>([])
const loading = ref(false)
async function run() {
  loading.value = true
  try {
    events.value = (await api('/reports/run?line_id=1', { method: 'POST' })).events || []
  } finally { loading.value = false }
}
onMounted(async () => {
  trips.value = await api('/trips')
  const reports = await api('/reports')
  if (reports.length) events.value = reports[0].events
  else await run()
})
function stripClass(s: string) {
  return s === 'bunching' ? 'bg-bunch' : s === 'large_gap' ? 'bg-large' : ''
}
function label(s: string) {
  return s === 'bunching' ? '串车' : s === 'large_gap' ? '大间隔' : '正常'
}
</script>
<template>
  <h1>串车报告</h1>
  <p class="sub">按实际到站间隔对照计划发车间隔 · 竖直条带展示 · 点击前班班次号查看该班到站</p>
  <button class="btn" :disabled="loading" @click="run">重新检测</button>
  <div class="bg-split" style="margin-top:1rem">
    <aside class="bg-trip-col">
      <h2>关联班次</h2>
      <div v-for="r in trips" :key="r.id ?? r.trip_no" class="bg-trip-row">
        <div>
          <div>{{ r.trip_no }}</div>
          <div class="bg-trip-meta">{{ r.vehicle_no }}</div>
        </div>
        <div class="bg-trip-meta">{{ r.planned_depart }}</div>
      </div>
    </aside>
    <div class="bg-strip-col">
      <article
        v-for="(e, i) in events"
        :key="i"
        class="bg-gap-strip"
        :class="stripClass(e.status)"
      >
        <header>{{ e.stop_name }} <span class="bg-trip-meta">站序 {{ e.stop_seq }}</span></header>
        <div class="bg-gap-body">
          <div class="bg-gap-val">{{ e.gap_min }}′</div>
          <div>计划 {{ e.planned_headway_min }}′</div>
          <div>
            <RouterLink class="bg-trip-link" :to="{ path: '/arrivals', query: { trip_no: e.earlier_trip } }">{{ e.earlier_trip }}</RouterLink>
            <span class="bg-trip-meta"> {{ e.earlier_vehicle }}</span>
            → {{ e.later_trip }} <span class="bg-trip-meta">{{ e.later_vehicle }}</span>
          </div>
          <span class="badge" :class="e.status === 'bunching' ? 'badge-bad' : e.status === 'large_gap' ? 'badge-warn' : 'badge-ok'">
            {{ label(e.status) }}
          </span>
        </div>
      </article>
      <p v-if="!events.length" class="muted">暂无间隔事件</p>
    </div>
  </div>
</template>
