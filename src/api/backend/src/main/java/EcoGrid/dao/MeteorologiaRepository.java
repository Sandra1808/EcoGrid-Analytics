package EcoGrid.dao;

import EcoGrid.entity.Meteorologia;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MeteorologiaRepository
        extends JpaRepository<Meteorologia, Long> {
}