<template>
  <PanoramaViewer
    :scene-id="sceneId"
    :return-floor-id="returnFloorId"
  />
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import PanoramaViewer from '@/components/PanoramaViewer.vue'

const route = useRoute()
const sceneId = computed(() => String(route.params.sceneId || 'scene1'))
const returnFloorId = computed(() => String(route.query.floor || 'overall'))
</script>
