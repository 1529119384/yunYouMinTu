<template>
  <TileImageViewer
    :initial-floor-id="initialFloorId"
    @floor-change="syncFloorRoute"
  />
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TileImageViewer from '@/components/TileImageViewer1-fixed.vue'

const route = useRoute()
const router = useRouter()
const initialFloorId = computed(() => String(route.params.floorId || 'overall'))

function syncFloorRoute(floorId) {
  router.replace({ name: 'floor-map', params: { floorId } })
}
</script>
