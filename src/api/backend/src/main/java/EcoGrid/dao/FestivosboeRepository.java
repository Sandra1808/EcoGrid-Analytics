package EcoGrid.dao;

import EcoGrid.entity.Festivosboe;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDate;

public interface FestivosboeRepository
        extends JpaRepository<Festivosboe, Long> {

    boolean existsByFechaAndAmbitoIgnoreCase(LocalDate fecha, String ambito);
}