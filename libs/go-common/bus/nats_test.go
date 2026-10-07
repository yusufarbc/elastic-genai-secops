package bus

import (
	"context"
	"os"
	"sync"
	"testing"
	"time"
)

// Integration test against a real NATS server; runs only when NATS_TEST_URL is set, e.g.
//
//	NATS_TEST_URL=nats://localhost:4222 go test ./libs/go-common/bus/
func TestSameMsgIDOnDifferentSubjectsIsDelivered(t *testing.T) {
	url := os.Getenv("NATS_TEST_URL")
	if url == "" {
		t.Skip("NATS_TEST_URL not set")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()

	b, err := NewNATS(ctx, url)
	if err != nil {
		t.Fatal(err)
	}
	defer b.Close()

	run := time.Now().Format("150405.000000")
	subjects := []string{"esm.test.a", "esm.test.b"}
	var mu sync.Mutex
	got := map[string]bool{}
	for _, s := range subjects {
		s := s
		go func() {
			_ = b.Subscribe(ctx, s, "test-"+s[len(s)-1:]+"-"+run[7:], func(_ context.Context, data []byte) error {
				if string(data) == `"`+run+`"` {
					mu.Lock()
					got[s] = true
					mu.Unlock()
				}
				return nil
			})
		}()
	}
	for _, s := range subjects {
		// Same message ID on both subjects: both must be stored and delivered.
		if err := b.Publish(ctx, s, "id-"+run, run); err != nil {
			t.Fatal(err)
		}
	}
	for ctx.Err() == nil {
		mu.Lock()
		done := len(got) == len(subjects)
		mu.Unlock()
		if done {
			return
		}
		time.Sleep(100 * time.Millisecond)
	}
	t.Fatalf("delivered on %v, want both %v", got, subjects)
}
