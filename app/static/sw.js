// 최소한의 서비스 워커: 홈 화면 추가(PWA 설치)를 지원하기 위한 용도입니다.
// 예약 데이터는 항상 최신 상태를 보여줘야 하므로 캐싱은 하지 않습니다.
self.addEventListener("install", (e) => self.skipWaiting());
self.addEventListener("activate", (e) => self.clients.claim());
self.addEventListener("fetch", (e) => {
  // 네트워크 요청을 그대로 통과시킴 (오프라인 캐싱 없음)
});
