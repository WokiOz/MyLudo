<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ youtubeId: string; title: string }>()
const playing = ref(false)
</script>

<template>
  <div class="player">
    <iframe
      v-if="playing"
      :src="`https://www.youtube-nocookie.com/embed/${youtubeId}?autoplay=1&rel=0&hl=fr&cc_lang_pref=fr`"
      :title="title"
      allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
      allowfullscreen
      referrerpolicy="strict-origin-when-cross-origin"
    ></iframe>
    <button v-else class="cover" :aria-label="`Lire la vidéo : ${title}`" @click="playing = true">
      <img
        :src="`https://i.ytimg.com/vi/${youtubeId}/hqdefault.jpg`"
        alt=""
        loading="lazy"
        referrerpolicy="no-referrer"
      />
      <span class="play" aria-hidden="true">▶</span>
    </button>
  </div>
</template>

<style scoped>
.player {
  position: relative;
  aspect-ratio: 16 / 9;
  width: 100%;
  border-radius: 10px;
  overflow: hidden;
  background: #000;
}
iframe,
.cover,
.cover img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border: 0;
  padding: 0;
  object-fit: cover;
}
.cover {
  border-radius: 0;
  background: #000;
}
.play {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  font-size: 2.4rem;
  color: #fff;
  text-shadow: 0 2px 12px rgb(0 0 0 / 0.6);
}
</style>
